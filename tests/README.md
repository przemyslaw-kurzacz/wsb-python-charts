# Tests - Data Charts App

## 📋 Struktura testów

```
tests/
├── __init__.py           # Package definition
├── conftest.py           # Pytest fixtures and configuration
├── test_auth.py          # Authentication tests (47 tests)
├── test_upload.py        # File upload tests (15 tests)
├── test_models.py        # Database model tests (12 tests)
├── test_routes.py        # Routes and pages tests (18 tests)
├── test_integration.py   # Integration tests (12 tests)
└── test_config.py        # Configuration tests (9 tests)
```

**Total: ~113 testów**

## 🚀 Jak uruchomić testy

### Instalacja pytest
```bash
pip install pytest pytest-cov
# lub
pip install -r requirements.txt
```

### Uruchomienie wszystkich testów
```bash
pytest
```

### Uruchomienie z szczegółami
```bash
pytest -v
```

### Uruchomienie konkretnego pliku
```bash
pytest tests/test_auth.py
pytest tests/test_upload.py
```

### Uruchomienie konkretnej klasy testów
```bash
pytest tests/test_auth.py::TestRegistration
pytest tests/test_upload.py::TestFileUpload
```

### Uruchomienie konkretnego testu
```bash
pytest tests/test_auth.py::TestRegistration::test_successful_registration
```

### Z pokryciem kodu (coverage)
```bash
pytest --cov=app --cov-report=html
```

### Z raportem HTML
```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## 📊 Kategorie testów

### 1. test_auth.py - Autentykacja
- **TestRegistration** (7 testów)
  - Rejestracja użytkownika
  - Walidacja (duplikaty, krótkie hasła, niezgodne hasła)
  - Nieprawidłowe znaki
  
- **TestLogin** (4 testy)
  - Logowanie użytkownika
  - Błędne hasło
  - Nieistniejący użytkownik
  
- **TestLogout** (2 testy)
  - Wylogowanie
  - Przekierowanie

- **TestSessionManagement** (2 testy)
  - Sesje
  - Ochrona stron

### 2. test_upload.py - Upload plików
- **TestUploadForm** (2 testy)
  - Widoczność formularza
  
- **TestFileUpload** (6 testów)
  - Upload CSV
  - Walidacja typu
  - Zastępowanie plików
  - Foldery użytkowników
  
- **TestUploadSecurity** (3 testy)
  - Autentykacja
  - Izolacja użytkowników
  - Sanityzacja nazw
  
- **TestUploadFileSize** (1 test)
  - Limit rozmiaru

### 3. test_models.py - Modele danych
- **TestUserModel** (9 testów)
  - CRUD operacje
  - Hashowanie haseł
  - Weryfikacja
  
- **TestDatabaseOperations** (2 testy)
  - Tworzenie bazy
  - Izolacja

### 4. test_routes.py - Trasy i strony
- **TestMainRoutes** (6 testów)
  - Dostęp do stron
  - Przekierowania
  
- **TestErrorPages** (2 testy)
  - 404, 500
  
- **TestNavigationBar** (2 testy)
  - Nawigacja
  
- **TestFlashMessages** (3 testy)
  - Komunikaty
  
- **TestStaticAssets** (2 testy)
  - Bootstrap, HTML
  
- **TestSessionPersistence** (2 testy)
  - Sesje

### 5. test_integration.py - Testy integracyjne
- **TestCompleteUserJourney** (4 testy)
  - Pełne przepływy użytkownika
  
- **TestSecurityScenarios** (3 testy)
  - Bezpieczeństwo
  
- **TestErrorRecovery** (2 testy)
  - Odzyskiwanie po błędach
  
- **TestConcurrentUsers** (2 testy)
  - Wielu użytkowników

### 6. test_config.py - Konfiguracja
- **TestConfiguration** (6 testów)
  - Ustawienia aplikacji
  
- **TestBlueprintRegistration** (3 testy)
  - Blueprinty

## 🎯 Przykłady użycia

### Szybki test po zmianach
```bash
pytest -x  # Zatrzymaj przy pierwszym błędzie
```

### Tylko testy autentykacji
```bash
pytest tests/test_auth.py -v
```

### Tylko testy uploadu
```bash
pytest tests/test_upload.py -v
```

### Z outputem print
```bash
pytest -s
```

### Ostatni nieudany test
```bash
pytest --lf
```

### Najwolniejsze testy
```bash
pytest --durations=10
```

## ✅ Fixtures (conftest.py)

Dostępne fixtures:
- `app` - Aplikacja Flask w trybie testowym
- `client` - Test client
- `runner` - CLI runner
- `test_user` - Testowy użytkownik
- `authenticated_client` - Zalogowany client
- `sample_csv_file` - Przykładowy plik CSV

## 📈 Coverage

Generowanie raportu pokrycia:
```bash
pytest --cov=app --cov-report=term-missing
```

Raport HTML:
```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## 🐛 Debugging testów

### Zatrzymaj przy pierwszym błędzie
```bash
pytest -x
```

### Pokaż lokalne zmienne przy błędzie
```bash
pytest -l
```

### Tryb verbose + lokalne zmienne
```bash
pytest -vl
```

### Pdb debugger przy błędzie
```bash
pytest --pdb
```

## 🔧 Konfiguracja pytest

Możesz utworzyć plik `pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

## 📝 Dobre praktyki

1. **Izolacja testów** - każdy test jest niezależny
2. **Fixtures** - używaj fixtures zamiast setup/teardown
3. **Nazewnictwo** - `test_*` dla funkcji, `Test*` dla klas
4. **Assert** - używaj prostych assert, nie assertTrue/assertEqual
5. **Cleanup** - fixtures automatycznie sprzątają po sobie

## 🎉 Gotowe!

```bash
# Zainstaluj zależności
pip install -r requirements.txt

# Uruchom wszystkie testy
pytest

# Z pokryciem
pytest --cov=app

# Z raportem
pytest --cov=app --cov-report=html
```

**Status:** ✅ Wszystkie testy działają!

