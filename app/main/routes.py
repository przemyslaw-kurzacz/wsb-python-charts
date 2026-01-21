from flask import render_template, redirect, url_for, session, flash, current_app, jsonify, send_file
from app.main import bp
from app.main.forms import UploadForm
from werkzeug.utils import secure_filename
import os
import glob
import io

from app.main.processing import (
    find_user_csv_file,
    parse_and_validate_csv,
    compute_statistics,
    generate_histogram_png,
)



@bp.route('/')
@bp.route('/index', methods=['GET', 'POST'])
def index():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    form = UploadForm()
    uploaded_file = None

    # Sprawdź czy użytkownik ma już przesłany plik
    user_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], session['username'])
    if os.path.exists(user_folder):
        user_files = glob.glob(os.path.join(user_folder, '*.csv'))
        if user_files:
            uploaded_file = os.path.basename(user_files[0])

    if form.validate_on_submit():
        file = form.file.data
        if file:
            # Utwórz folder dla użytkownika jeśli nie istnieje
            if not os.path.exists(user_folder):
                os.makedirs(user_folder)

            # Usuń wszystkie poprzednie pliki użytkownika (tylko jeden plik dozwolony)
            for old_file in glob.glob(os.path.join(user_folder, '*.csv')):
                try:
                    os.remove(old_file)
                except Exception as e:
                    flash(f'Błąd podczas usuwania starego pliku: {str(e)}', 'warning')

            # Zapisz nowy plik
            filename = secure_filename(file.filename)
            filepath = os.path.join(user_folder, filename)
            try:
                file.save(filepath)
                flash(f'Plik "{filename}" został pomyślnie przesłany!', 'success')
                return redirect(url_for('main.index'))
            except Exception as e:
                flash(f'Błąd podczas zapisywania pliku: {str(e)}', 'danger')

    return render_template('index.html', title='Strona główna', form=form, uploaded_file=uploaded_file)

@bp.route('/api/stats', methods=['GET'])
def api_stats():
    """Return JSON statistics for the current user's uploaded CSV."""
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    user_csv = find_user_csv_file(current_app.config['UPLOAD_FOLDER'], session['username'])
    if not user_csv:
        return jsonify({'error': 'No CSV file uploaded'}), 400

    try:
        df = parse_and_validate_csv(user_csv)
        stats = compute_statistics(df)
        return jsonify(stats), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception:
        return jsonify({'error': 'Internal processing error'}), 500


@bp.route('/api/plot', methods=['GET'])
def api_plot():
    """Return a PNG histogram for the first numeric column."""
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    user_csv = find_user_csv_file(current_app.config['UPLOAD_FOLDER'], session['username'])
    if not user_csv:
        return jsonify({'error': 'No CSV file uploaded'}), 400

    try:
        df = parse_and_validate_csv(user_csv)
        png_bytes = generate_histogram_png(df)
        return send_file(
            io.BytesIO(png_bytes),
            mimetype='image/png',
            as_attachment=False,
            download_name='hist.png',
        )
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception:
        return jsonify({'error': 'Internal processing error'}), 500

