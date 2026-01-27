from flask import (
    render_template,
    redirect,
    url_for,
    session,
    flash,
    current_app,
    jsonify,
    send_file,
    request,
)
from app.main import bp
from app.main.forms import UploadForm
from werkzeug.utils import secure_filename

import os
import glob
import io
import json

from plotly.utils import PlotlyJSONEncoder

from app.main.processing import (
    find_user_csv_file,
    parse_and_validate_csv,
    compute_statistics,
    generate_histogram_png,
    basic_prepare_dataframe,
    detect_columns,
)

from app.main import plotly_charts


def _load_current_user_df():
    """Helper: load and prepare the current user's DataFrame (or return None)."""
    user_csv = find_user_csv_file(current_app.config["UPLOAD_FOLDER"], session.get("username", ""))
    if not user_csv:
        return None
    df_raw = parse_and_validate_csv(user_csv)
    return basic_prepare_dataframe(df_raw)


def _build_metadata(df):
    import pandas as pd

    dtypes = {c: str(df[c].dtype) for c in df.columns}
    numeric = df.select_dtypes(include="number").columns.tolist()
    categorical = [c for c in df.columns if c not in numeric]

    numeric_ranges = {}
    for c in numeric:
        s = df[c].dropna()
        if not s.empty:
            numeric_ranges[c] = {"min": float(s.min()), "max": float(s.max())}

    # dla kategorycznych zwracamy tylko top wartości (dla UI multi-select)
    cat_values = {}
    for c in categorical:
        vc = df[c].astype(str).value_counts(dropna=False).head(200)
        cat_values[c] = vc.index.tolist()

    return {
        "columns": df.columns.tolist(),
        "dtypes": dtypes,
        "numeric_columns": numeric,
        "categorical_columns": categorical,
        "numeric_ranges": numeric_ranges,
        "categorical_values": cat_values,
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
    }


@bp.route("/", methods=["GET", "POST"])
@bp.route("/index", methods=["GET", "POST"])
def index():
    """Strona główna: upload CSV + interaktywny dashboard z filtrami."""
    if "username" not in session:
        return redirect(url_for("auth.login"))

    form = UploadForm()
    uploaded_file = None

    # 1) czy user ma już plik
    user_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], session["username"])
    if os.path.exists(user_folder):
        user_files = glob.glob(os.path.join(user_folder, "*.csv"))
        if user_files:
            uploaded_file = os.path.basename(user_files[0])

    # 2) upload
    if form.validate_on_submit():
        file = form.file.data
        if file:
            if not os.path.exists(user_folder):
                os.makedirs(user_folder)

            for old_file in glob.glob(os.path.join(user_folder, "*.csv")):
                try:
                    os.remove(old_file)
                except Exception as e:
                    flash(f'Błąd podczas usuwania starego pliku: {str(e)}', "warning")

            filename = secure_filename(file.filename)
            filepath = os.path.join(user_folder, filename)

            try:
                file.save(filepath)
                flash(f'Plik "{filename}" został pomyślnie przesłany!', "success")
                return redirect(url_for("main.index"))
            except Exception as e:
                flash(f'Błąd podczas zapisywania pliku: {str(e)}', "danger")

    # 3) dashboard data
    stats = None
    message = None
    metadata = None
    initial_figs = {}

    user_csv = find_user_csv_file(current_app.config["UPLOAD_FOLDER"], session["username"])
    if user_csv:
        try:
            df_raw = parse_and_validate_csv(user_csv)
            stats = compute_statistics(df_raw)
            df_ready = basic_prepare_dataframe(df_raw)

            metadata = _build_metadata(df_ready)

            numeric_col, categorical_col = detect_columns(df_ready)

            # Wstępne wykresy (żeby strona nie była pusta)
            if numeric_col:
                initial_figs["histogram"] = plotly_charts.histogram(df_ready, column=numeric_col, bins=30)
                initial_figs["box"] = plotly_charts.boxplot(df_ready, column=numeric_col)

            if categorical_col:
                initial_figs["bar_counts"] = plotly_charts.bar_counts(df_ready, column=categorical_col, top_n=20)

            heat = plotly_charts.corr_heatmap(df_ready)
            if heat:
                initial_figs["corr_heatmap"] = heat

        except Exception as e:
            message = f"Błąd podczas przetwarzania CSV: {str(e)}"

    # Plotly figures may contain numpy arrays (ndarray). Jinja's `tojson` filter
    # uses Flask's JSON encoder, which doesn't handle ndarrays by default.
    # We pre-serialize figures using Plotly's encoder.
    initial_figs_json = json.dumps(initial_figs, cls=PlotlyJSONEncoder)

    return render_template(
        "index.html",
        title="Strona główna",
        form=form,
        uploaded_file=uploaded_file,
        stats=stats,
        metadata=metadata,
        initial_figs=initial_figs,
        initial_figs_json=initial_figs_json,
        message=message,
    )


@bp.route("/api/metadata", methods=["GET"])
def api_metadata():
    """Zwraca metadane datasetu do budowy filtrów na froncie."""
    if "username" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        df = _load_current_user_df()
        if df is None:
            return jsonify({"error": "No CSV file uploaded"}), 400
        return jsonify(_build_metadata(df)), 200
    except Exception:
        return jsonify({"error": "Internal processing error"}), 500


@bp.route("/api/chart", methods=["GET"])
def api_chart():
    """Zwraca wykres Plotly (JSON) na podstawie parametrów query.

    Przykłady:
      /api/chart?type=histogram&column=price&bins=40
      /api/chart?type=scatter&x=a&y=b&color=category
      /api/chart?type=bar_counts&column=city&top_n=30

    Filtr (jeden naraz, w wersji minimalnej):
      filter_column=... & filter_min=... & filter_max=...
      filter_column=... & filter_values=A,B,C
      filter_column=... & filter_op=contains & filter_value=foo
    """
    if "username" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    chart_type = request.args.get("type", "").strip()

    try:
        df = _load_current_user_df()
        if df is None:
            return jsonify({"error": "No CSV file uploaded"}), 400

        # --- common filters ---
        filter_column = request.args.get("filter_column")
        filter_min = request.args.get("filter_min")
        filter_max = request.args.get("filter_max")
        filter_op = request.args.get("filter_op")
        filter_value = request.args.get("filter_value")
        filter_values = request.args.get("filter_values")

        fmin = float(filter_min) if filter_min not in (None, "", "null") else None
        fmax = float(filter_max) if filter_max not in (None, "", "null") else None
        fvals = [v for v in (filter_values.split(",") if filter_values else []) if v != ""]

        if chart_type == "histogram":
            column = request.args.get("column")
            bins = int(request.args.get("bins", "30"))
            return jsonify(
                plotly_charts.histogram(
                    df,
                    column=column,
                    bins=bins,
                    filter_column=filter_column,
                    filter_min=fmin,
                    filter_max=fmax,
                    filter_values=fvals or None,
                    filter_op=filter_op,
                    filter_value=filter_value,
                )
            ), 200

        if chart_type == "box":
            column = request.args.get("column")
            by = request.args.get("by")
            return jsonify(
                plotly_charts.boxplot(
                    df,
                    column=column,
                    by=by,
                    filter_column=filter_column,
                    filter_min=fmin,
                    filter_max=fmax,
                    filter_values=fvals or None,
                    filter_op=filter_op,
                    filter_value=filter_value,
                )
            ), 200

        if chart_type == "bar_counts":
            column = request.args.get("column")
            top_n = int(request.args.get("top_n", "20"))
            return jsonify(
                plotly_charts.bar_counts(
                    df,
                    column=column,
                    top_n=top_n,
                    filter_column=filter_column,
                    filter_min=fmin,
                    filter_max=fmax,
                    filter_values=fvals or None,
                    filter_op=filter_op,
                    filter_value=filter_value,
                )
            ), 200

        if chart_type == "scatter":
            x = request.args.get("x")
            y = request.args.get("y")
            color = request.args.get("color")
            return jsonify(
                plotly_charts.scatter(
                    df,
                    x=x,
                    y=y,
                    color=color,
                    filter_column=filter_column,
                    filter_min=fmin,
                    filter_max=fmax,
                    filter_values=fvals or None,
                    filter_op=filter_op,
                    filter_value=filter_value,
                )
            ), 200

        if chart_type == "corr_heatmap":
            fig = plotly_charts.corr_heatmap(df)
            if fig is None:
                return jsonify({"error": "Not enough numeric columns"}), 400
            return jsonify(fig), 200

        return jsonify({"error": "Unknown chart type"}), 400

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "Internal processing error"}), 500


@bp.route("/api/stats", methods=["GET"])
def api_stats():
    """Return JSON statistics for the current user's uploaded CSV."""
    if "username" not in session:
        return redirect(url_for("auth.login"))

    user_csv = find_user_csv_file(current_app.config["UPLOAD_FOLDER"], session["username"])
    if not user_csv:
        return jsonify({"error": "No CSV file uploaded"}), 400

    try:
        df = parse_and_validate_csv(user_csv)
        stats = compute_statistics(df)
        return jsonify(stats), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "Internal processing error"}), 500


@bp.route("/api/plot", methods=["GET"])
def api_plot():
    """Return a PNG histogram for the first numeric column (legacy endpoint)."""
    if "username" not in session:
        return redirect(url_for("auth.login"))

    user_csv = find_user_csv_file(current_app.config["UPLOAD_FOLDER"], session["username"])
    if not user_csv:
        return jsonify({"error": "No CSV file uploaded"}), 400

    try:
        df = parse_and_validate_csv(user_csv)
        png_bytes = generate_histogram_png(df)
        return send_file(
            io.BytesIO(png_bytes),
            mimetype="image/png",
            as_attachment=False,
            download_name="hist.png",
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "Internal processing error"}), 500
