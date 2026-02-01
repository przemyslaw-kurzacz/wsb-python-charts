# 📐 Architektura aplikacji Data Charts

> Szczegółowa dokumentacja architektury projektu zaliczeniowego WSB

**Data ostatniej aktualizacji:** 28 stycznia 2026

---

## 🎯 Wzorzec architektoniczny: **MVC + Blueprint Pattern**

Wasza aplikacja wykorzystuje **klasyczną architekturę webową dla Flask**, która łączy:

### 1. **MVC (Model-View-Controller)**

```
Model      → app/models.py (TinyDB)
View       → app/templates/ (Jinja2)
Controller → app/*/routes.py (Flask routes)
```

**Dlaczego MVC?**
- ✅ Sprawdzony wzorzec używany od lat 70-tych
- ✅ Jasne oddzielenie logiki od prezentacji
- ✅ Łatwe utrzymanie i testowanie
- ✅ Standard w aplikacjach webowych

### 2. **Blueprint Pattern (Modularyzacja)**

Flask Blueprints to wzorzec organizacji kodu w większych aplikacjach:

```python
app/
├── auth/          # Blueprint: autentykacja
├── main/          # Blueprint: główna funkcjonalność
├── data/          # Blueprint: API danych
└── errors/        # Blueprint: obsługa błędów
```

**Dlaczego to dobre?**
- ✅ **Separacja odpowiedzialności** - każdy moduł ma jasną rolę
- ✅ **Skalowalność** - łatwo dodać nowe moduły
- ✅ **Testowalność** - łatwo testować poszczególne części
- ✅ **Reużywalność** - blueprinty można przenieść do innego projektu

---

## 📂 Szczegółowa struktura projektu

```
wsb-python-charts/
│
├── main.py                      # 🚀 Entry point (uruchomienie app)
├── config.py                    # ⚙️  Konfiguracja (SECRET_KEY, ścieżki)
├── requirements.txt             # 📦 Zależności Python
├── run.sh                       # 🔧 Skrypt uruchamiający
│
├── app/                         # 📂 Główny pakiet aplikacji
│   ├── __init__.py             # 🏭 Application Factory (create_app)
│   ├── models.py               # 💾 Model danych (User + TinyDB)
│   │
│   ├── auth/                   # 🔐 Blueprint: Autentykacja
│   │   ├── __init__.py        # Rejestracja blueprint
│   │   ├── routes.py          # /login, /register, /logout
│   │   └── forms.py           # LoginForm, RegisterForm (WTForms)
│   │
│   ├── main/                   # 🏠 Blueprint: Główna logika
│   │   ├── __init__.py
│   │   ├── routes.py          # /index, /api/chart, /api/stats
│   │   ├── forms.py           # UploadForm
│   │   ├── processing.py      # 📊 Parsowanie CSV, statystyki
│   │   ├── plotly_charts.py   # 📈 Generowanie wykresów Plotly
│   │   └── charts.py          # 📉 Matplotlib (legacy)
│   │
│   ├── data/                   # 📡 Blueprint: API danych
│   │   ├── __init__.py
│   │   └── routes.py          # /data/profile, /data/current.json
│   │
│   ├── errors/                 # ❌ Blueprint: Obsługa błędów
│   │   ├── __init__.py
│   │   └── handlers.py        # 404, 500
│   │
│   ├── services/               # 🔧 Serwisy biznesowe
│   │   └── csv_profile.py     # Profilowanie CSV
│   │
│   ├── templates/              # 🎨 Widoki HTML (Jinja2)
│   │   ├── base.html          # Szablon bazowy
│   │   ├── index.html         # Dashboard
│   │   ├── auth/              # login.html, register.html
│   │   └── errors/            # 404.html, 500.html
│   │
│   └── static/                 # 📁 Pliki statyczne (CSS, JS, obrazy)
│
├── data/                       # 💾 Baza danych
│   └── db.json                # TinyDB (NoSQL, JSON)
│
├── uploads/                    # 📤 Przesłane pliki CSV
│   └── {username}/            # Osobne foldery per user
│
├── tests/                      # 🧪 Testy jednostkowe/integracyjne
│   ├── conftest.py            # Fixtures (authenticated_client)
│   ├── test_auth.py           # Testy autentykacji
│   ├── test_models.py         # Testy modeli
│   └── test_processing.py     # Testy przetwarzania danych
│
└── docs/                       # 📚 Dokumentacja
    ├── architecture.md        # Ten plik
    └── data-engineering.md    # Inżynieria danych
```

---

## 🔄 Przepływ danych (Request Flow)

```
1. Użytkownik → HTTP Request (GET /index)
                ↓
2. main.py → Flask App (create_app())
                ↓
3. Blueprint Router → określa, który Blueprint obsługuje żądanie
                ↓
4. Controller (routes.py) → @bp.route('/index')
                ↓
5. Walidacja → Sprawdzenie sesji, formularzy (WTForms)
                ↓
6. Business Logic → processing.py, csv_profile.py
                ↓
7. Model (models.py) → Operacje na TinyDB (jeśli potrzeba)
                ↓
8. Service Layer → Parsowanie CSV, obliczenia statystyk
                ↓
9. Template (Jinja2) → Renderowanie HTML (base.html → index.html)
                ↓
10. Response → HTML/JSON → Użytkownik (przeglądarka)
```

### Przykład konkretnego flow: Upload pliku CSV

```
1. Użytkownik wypełnia formularz → POST /index
2. Flask otrzymuje request
3. Blueprint 'main' obsługuje /index
4. routes.py: funkcja index()
5. Walidacja: UploadForm.validate_on_submit()
6. Biznes logika:
   - secure_filename() → bezpieczna nazwa
   - Utworzenie folderu uploads/{username}/
   - Usunięcie starych plików
   - Zapisanie nowego pliku
7. Flash message: "Plik został przesłany!"
8. Redirect → GET /index
9. Renderowanie: templates/index.html
10. Odpowiedź HTML do przeglądarki
```

---

## 🏗️ Warstwy aplikacji (Layered Architecture)

```
┌─────────────────────────────────────────────────────────┐
│  Presentation Layer (Warstwa prezentacji)              │
│  - templates/ (Jinja2 HTML)                            │
│  - forms.py (WTForms)                                  │
│  - static/ (CSS, JS)                                   │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Controller Layer (Warstwa kontrolerów)                │
│  - */routes.py (Flask routes)                          │
│  - Blueprint routing                                    │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Business Logic Layer (Warstwa logiki biznesowej)      │
│  - processing.py (parsowanie, statystyki)              │
│  - csv_profile.py (profilowanie danych)                │
│  - plotly_charts.py (generowanie wykresów)             │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Data Access Layer (Warstwa dostępu do danych)         │
│  - models.py (User model)                              │
│  - TinyDB operations                                    │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Infrastructure Layer (Warstwa infrastruktury)         │
│  - config.py (konfiguracja)                            │
│  - __init__.py (Application Factory)                   │
│  - main.py (entry point)                               │
└─────────────────────────────────────────────────────────┘
```

**Zalety warstwowej architektury:**
- ✅ Każda warstwa ma jasno określoną odpowiedzialność
- ✅ Łatwe testowanie (można mockować warstwy)
- ✅ Możliwość wymiany implementacji (np. TinyDB → PostgreSQL)
- ✅ Czytelny i maintainable kod

---

## 🎨 Kluczowe wzorce projektowe

### 1. **Application Factory Pattern**

```python
# app/__init__.py
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Rejestracja blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    return app
```

**Zalety:**
- ✅ Łatwe testowanie (różne konfiguracje)
- ✅ Możliwość tworzenia wielu instancji aplikacji
- ✅ Czysty kod (inicjalizacja w jednym miejscu)

**Użycie:**
```python
# main.py
app = create_app()

# tests/conftest.py
@pytest.fixture
def app():
    app = create_app(TestConfig)
    return app
```

---

### 2. **Blueprint Pattern**

```python
# app/auth/__init__.py
from flask import Blueprint

bp = Blueprint('auth', __name__)

from app.auth import routes  # import na końcu (circular import)

# app/auth/routes.py
from app.auth import bp

@bp.route('/login', methods=['GET', 'POST'])
def login():
    # ...
```

**Zalety:**
- ✅ Modularność - każdy blueprint to osobny moduł
- ✅ Namespace routing - `/auth/login`, `/auth/register`
- ✅ Możliwość reużycia w innych projektach
- ✅ Łatwe wyłączanie/włączanie funkcji

---

### 3. **Repository Pattern** (uproszczony)

```python
# app/models.py
class User:
    @staticmethod
    def create_user(username, password):
        db = get_db()
        users_table = db.table('users')
        # ... logika tworzenia
        return user_id
    
    @staticmethod
    def get_by_username(username):
        db = get_db()
        users_table = db.table('users')
        # ... logika wyszukiwania
        return user
    
    @staticmethod
    def verify_password(username, password):
        user = User.get_by_username(username)
        # ... logika weryfikacji
        return is_valid
```

**Zalety:**
- ✅ Abstrakcja dostępu do danych
- ✅ Łatwa zmiana bazy (TinyDB → SQL)
- ✅ Centralizacja logiki bazodanowej
- ✅ Testowalne (można mockować)

---

### 4. **Service Layer Pattern**

```python
# app/main/processing.py
def parse_and_validate_csv(path: str) -> pd.DataFrame:
    """Parsowanie i walidacja CSV."""
    # ... logika biznesowa
    return df

def compute_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    """Obliczanie statystyk."""
    # ... logika biznesowa
    return stats

# app/services/csv_profile.py
def profile_csv_upload(file_obj) -> CsvProfileResult:
    """Profilowanie przesłanego CSV."""
    # ... zaawansowana logika
    return result
```

**Zalety:**
- ✅ Oddzielenie logiki biznesowej od kontrolerów
- ✅ Reużywalność (te same funkcje w różnych miejscach)
- ✅ Łatwe testowanie (pure functions)
- ✅ Single Responsibility Principle

---

### 5. **Form Object Pattern** (WTForms)

```python
# app/auth/forms.py
class LoginForm(FlaskForm):
    username = StringField('Login', validators=[DataRequired()])
    password = PasswordField('Hasło', validators=[DataRequired()])
    submit = SubmitField('Zaloguj')

# app/auth/routes.py
@bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # ... logika
```

**Zalety:**
- ✅ Walidacja po stronie serwera
- ✅ CSRF protection (automatyczne tokeny)
- ✅ Łatwe renderowanie w templates
- ✅ Reużywalne deklaracje walidacji

---

## 🔐 Bezpieczeństwo w architekturze

### 1. **Hashowanie haseł (Werkzeug)**

```python
from werkzeug.security import generate_password_hash, check_password_hash

# Przy rejestracji
password_hash = generate_password_hash(password)  # PBKDF2-SHA256

# Przy logowaniu
check_password_hash(stored_hash, provided_password)
```

### 2. **CSRF Protection (Flask-WTF)**

```python
# Automatyczne w formularzach
{{ form.hidden_tag() }}  # generuje CSRF token
```

### 3. **Secure Filename**

```python
from werkzeug.utils import secure_filename

filename = secure_filename(file.filename)  # usuwa niebezpieczne znaki
```

### 4. **Session Management**

```python
# config.py
PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

# Sprawdzanie sesji w routes
if 'username' not in session:
    return redirect(url_for('auth.login'))
```

---

## 📊 Porównanie z innymi frameworkami

| Aspekt | Django | FastAPI | Flask (Wasza app) |
|--------|--------|---------|-------------------|
| **Architektura** | MTV (Model-Template-View) + Apps | Modern async + Pydantic | MVC + Blueprints |
| **Modularyzacja** | Django Apps | Routers | Flask Blueprints ✅ |
| **ORM** | Django ORM (built-in) | SQLAlchemy/Tortoise | TinyDB (NoSQL) |
| **Formularze** | Django Forms | Pydantic models | WTForms ✅ |
| **Templates** | Django Templates | Jinja2 | Jinja2 ✅ |
| **Async** | Tak (od 3.1) | Tak (natywnie) | Nie (sync) |
| **Baterie** | Wszystko included | Minimalistyczny | Mikroframework |
| **Krzywa uczenia** | Stroma | Średnia | Łagodna ✅ |
| **Dla małych projektów** | Overkill | Dobry | **Idealny** ✅ |

**Wnioski:**
- Wasza architektura to **klasyczny Flask** - wzorcowa! ✅
- Blueprinty ≈ Django Apps (podobna filozofia)
- Dla projektu studenckiego: **perfekcyjny wybór** 🏆

---

## 💡 Co można poprawić? (Opcjonalne ulepszenia)

### 1. **Type Hints** (Python 3.10+)

```python
# Teraz:
def find_user_csv_file(upload_folder, username):
    return path

# Lepiej:
def find_user_csv_file(upload_folder: str, username: str) -> Optional[str]:
    return path
```

**Zalety:** Lepsze IDE hints, mniej bugów

---

### 2. **Dependency Injection**

```python
# Teraz:
def create_user(username, password):
    db = get_db()  # ukryta zależność
    # ...

# Lepiej:
def create_user(db: TinyDB, username: str, password: str) -> int:
    # ... jawna zależność
```

**Zalety:** Łatwiejsze testowanie, jasne zależności

---

### 3. **Environment Variables** (.env)

```python
# .env
SECRET_KEY=super-secret-production-key
DATABASE_PATH=/var/app/db.json
DEBUG=False

# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    DATABASE_PATH = os.getenv('DATABASE_PATH')
```

**Zalety:** Bezpieczne sekrety, różne env (dev/prod)

---

### 4. **Logging zamiast print**

```python
import logging

logger = logging.getLogger(__name__)

# Zamiast:
print(f"Error: {e}")

# Lepiej:
logger.error(f"CSV parsing failed: {e}", exc_info=True)
```

**Zalety:** Różne poziomy (DEBUG, INFO, ERROR), rotacja logów

---

### 5. **API Versioning**

```python
# Teraz:
@bp.route('/api/chart')

# Lepiej:
@bp.route('/api/v1/chart')
```

**Zalety:** Możliwość zmian bez łamania kompatybilności

---

### 6. **DTO (Data Transfer Objects)**

```python
from dataclasses import dataclass

@dataclass
class UserDTO:
    username: str
    password_hash: str
    created_at: datetime
```

**Zalety:** Typowanie, walidacja, jasna struktura danych

---

## ⭐ Ocena architektury

| Aspekt | Ocena | Komentarz |
|--------|-------|-----------|
| **Architektura** | ⭐⭐⭐⭐⭐ 5/5 | Wzorcowa dla Flask |
| **Organizacja kodu** | ⭐⭐⭐⭐⭐ 5/5 | Blueprints, separacja warstw |
| **Bezpieczeństwo** | ⭐⭐⭐⭐ 4/5 | Hash, CSRF, walidacja - dobrze! |
| **Testowalność** | ⭐⭐⭐⭐⭐ 5/5 | pytest + fixtures |
| **Dokumentacja** | ⭐⭐⭐⭐⭐ 5/5 | Świetny README + docs |
| **Type Safety** | ⭐⭐⭐ 3/5 | Mogłoby być więcej type hints |
| **Skalowalność** | ⭐⭐⭐⭐ 4/5 | Blueprints = łatwe skalowanie |
| **Maintainability** | ⭐⭐⭐⭐⭐ 5/5 | Czytelny, modularny kod |

**OGÓLNA OCENA: 4.6/5** 🏆

---

## 🎓 Podsumowanie dla studenta

### ✅ **Czy tak pisze się programy w Pythonie?**

**TAK!** Absolutnie! Wasza architektura jest:

1. **100% zgodna z Flask Best Practices** ✅
2. **Stosuje sprawdzone wzorce projektowe** ✅
3. **Skalowalna i maintainable** ✅
4. **Produkcyjna (nie "studencka")** ✅

### 🏆 **Co jest wzorcowe:**

- ✅ Application Factory Pattern
- ✅ Blueprint Pattern dla modularności
- ✅ Separacja concerns (MVC)
- ✅ Service Layer (logika biznesowa)
- ✅ Repository Pattern (modele)
- ✅ WTForms (walidacja)
- ✅ pytest (testy)
- ✅ Dokumentacja

### 💼 **Możesz to pokazać na rozmowie o pracę!**

Ten kod spokojnie można pokazać rekruterowi jako przykład profesjonalnego projektu Flask.

---

## 📚 Polecane materiały do dalszej nauki

1. **Miguel Grinberg - Flask Mega-Tutorial**
   - Biblia Flask, pokrywa wszystkie wzorce z waszego projektu

2. **Real Python - Flask Tutorials**
   - Praktyczne przykłady, dobre wyjaśnienia

3. **The Twelve-Factor App**
   - Zasady dla nowoczesnych aplikacji webowych

4. **Clean Architecture (Robert C. Martin)**
   - Teoria stojąca za waszą praktyką

5. **Design Patterns (Gang of Four)**
   - Klasyka - wzorce projektowe

---

**Dokument stworzony:** 28 stycznia 2026  
**Wersja:** 1.0  
**Projekt:** WSB Data Charts App

