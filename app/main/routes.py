from flask import (
    render_template,
    redirect,
    url_for,
    session,
    flash,
    current_app,
    jsonify,
    send_file,
)
from app.main import bp
from app.main.forms import UploadForm
from werkzeug.utils import secure_filename
from app.main.charts import create_correlation_heatmap

import os
import glob
import io

from app.main.processing import (
    find_user_csv_file,
    parse_and_validate_csv,
    compute_statistics,
    generate_histogram_png,
    basic_prepare_dataframe,
    detect_columns,
)

from app.main.charts import (
    create_histogram,
    create_boxplot,
    create_barplot_counts,
)


@bp.route("/", methods=["GET", "POST"])
@bp.route("/index", methods=["GET", "POST"])
def index():
    """Strona główna: upload CSV + wizualizacje na tej samej stronie."""
    if "username" not in session:
        return redirect(url_for("auth.login"))

    form = UploadForm()
    uploaded_file = None

    # Krok 1: sprawdzamy czy użytkownik ma już plik CSV w swoim folderze
    user_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], session["username"])
    if os.path.exists(user_folder):
        user_files = glob.glob(os.path.join(user_folder, "*.csv"))
        if user_files:
            uploaded_file = os.path.basename(user_files[0])

    # Krok 2: obsługa uploadu (POST)
    if form.validate_on_submit():
        file = form.file.data
        if file:
            # Utwórz folder dla użytkownika jeśli nie istnieje
            if not os.path.exists(user_folder):
                os.makedirs(user_folder)

            # Usuń wszystkie poprzednie pliki użytkownika (tylko jeden plik dozwolony)
            for old_file in glob.glob(os.path.join(user_folder, "*.csv")):
                try:
                    os.remove(old_file)
                except Exception as e:
                    flash(f'Błąd podczas usuwania starego pliku: {str(e)}', "warning")

            # Zapisz nowy plik
            filename = secure_filename(file.filename)
            filepath = os.path.join(user_folder, filename)

            try:
                file.save(filepath)
                flash(f'Plik "{filename}" został pomyślnie przesłany!', "success")
                # Redirect -> po to, żeby odświeżenie strony nie wysyłało formularza ponownie
                return redirect(url_for("main.index"))
            except Exception as e:
                flash(f'Błąd podczas zapisywania pliku: {str(e)}', "danger")

    # Krok 3: jeśli jest CSV -> parsujemy dane, przygotowujemy i generujemy wykresy
    charts = {}
    stats = None
    message = None

    user_csv = find_user_csv_file(current_app.config["UPLOAD_FOLDER"], session["username"])
    if user_csv:
        try:
            # 3.1 Wczytanie CSV do DataFrame
            df_raw = parse_and_validate_csv(user_csv)

            # 3.2 Podstawowe statystyki (jako podsumowanie na stronie)
            stats = compute_statistics(df_raw)

            # 3.3 Podstawowe przygotowanie danych do wykresów (typy + braki danych)
            df_ready = basic_prepare_dataframe(df_raw)

            # 3.4 Wykrycie sensownych kolumn
            numeric_col, categorical_col = detect_columns(df_ready)

            # 3.5 Tworzenie wykresów
            if numeric_col:
                charts["Histogram (numeryczna)"] = create_histogram(df_ready, numeric_col)
                charts["Boxplot (numeryczna)"] = create_boxplot(df_ready, numeric_col)

            if categorical_col:
                charts["Barplot liczności (kategoryczna)"] = create_barplot_counts(
                    df_ready, categorical_col
                )

            # 3.6 Bonusowy wykres – heatmapa korelacji
            heatmap = create_correlation_heatmap(df_ready)
            if heatmap:
                charts["Heatmapa korelacji"] = heatmap


            if not charts:
                message = "Nie udało się znaleźć kolumn numerycznych lub kategorycznych do wykresów."

        except Exception as e:
            # Nie wywalamy całej strony - pokazujemy komunikat użytkownikowi
            message = f"Błąd podczas przetwarzania CSV: {str(e)}"

    return render_template(
        "index.html",
        title="Strona główna",
        form=form,
        uploaded_file=uploaded_file,
        stats=stats,
        charts=charts,
        message=message,
    )


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
    """Return a PNG histogram for the first numeric column."""
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

