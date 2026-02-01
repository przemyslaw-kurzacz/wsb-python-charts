# 📊 Data Engineering - Przetwarzanie i czyszczenie danych

> Dokumentacja techniczna procesu inżynierii danych w projekcie Data Charts

**Data:** 28 stycznia 2026  
**Wersja:** 1.0

---

## 🎯 Cel dokumentu

Ten dokument opisuje **jak przetwarzamy i czyścimy dane CSV** w naszej aplikacji:
- Jakie problemy rozwiązujemy
- Jakie techniki stosujemy
- Jakie biblioteki używamy
- Jak to działa pod maską

---

## 📋 Spis treści

1. [Pipeline przetwarzania danych](#-pipeline-przetwarzania-danych)
2. [Etap 1: Upload i walidacja](#-etap-1-upload-i-walidacja)
3. [Etap 2: Detekcja formatu](#-etap-2-detekcja-formatu)
4. [Etap 3: Parsowanie](#-etap-3-parsowanie)
5. [Etap 4: Czyszczenie danych](#-etap-4-czyszczenie-danych)
6. [Etap 5: Profilowanie kolumn](#-etap-5-profilowanie-kolumn)
7. [Etap 6: Przygotowanie do wizualizacji](#-etap-6-przygotowanie-do-wizualizacji)
8. [Problemy i rozwiązania](#-problemy-i-rozwiązania)
9. [Przykłady](#-przykłady)

---

## 🔄 Pipeline przetwarzania danych

```
┌─────────────────────────────────────────────────────────────┐
│  1. UPLOAD                                                  │
│  Użytkownik przesyła plik CSV przez formularz              │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  2. WALIDACJA                                               │
│  - Rozmiar pliku (max 16MB)                                │
│  - Rozszerzenie (.csv)                                      │
│  - Plik nie jest pusty                                      │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  3. DETEKCJA FORMATU                                        │
│  - Encoding (UTF-8, UTF-8-BOM, CP1250)                     │
│  - Delimiter (przecinek, średnik, tab)                      │
│  - Czy ma nagłówki                                          │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  4. PARSOWANIE                                              │
│  - pandas.read_csv() z wykrytymi parametrami               │
│  - Obsługa błędów kodowania                                 │
│  - Obsługa duplikatów kolumn                                │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  5. CZYSZCZENIE DANYCH                                      │
│  - Normalizacja pustych wartości (→ pd.NA)                 │
│  - Konwersja typów (tekst → liczba)                        │
│  - Detekcja dat                                             │
│  - Uzupełnianie braków (mediana/tekst)                     │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  6. PROFILOWANIE                                            │
│  - Typy kolumn (numeric, categorical, datetime)            │
│  - Statystyki (min, max, mean, missing)                    │
│  - Sugestie do wizualizacji                                 │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  7. PRZYGOTOWANIE DO WIZUALIZACJI                          │
│  - Filtrowanie danych                                       │
│  - Agregacje                                                │
│  - Generowanie wykresów (Plotly/Matplotlib)                │
└─────────────────────────────────────────────────────────────┘
```

---

## 📤 Etap 1: Upload i walidacja

### Kod: `app/main/routes.py`

```python
@bp.route('/', methods=['GET', 'POST'])
def index():
    form = UploadForm()
    
    if form.validate_on_submit():
        file = form.file.data
        
        # Walidacja rozszerzenia (WTForms)
        # FileAllowed(['csv'])
        
        # Bezpieczna nazwa
        filename = secure_filename(file.filename)
        
        # Zapisanie w folderze użytkownika
        user_folder = os.path.join(UPLOAD_FOLDER, session['username'])
        os.makedirs(user_folder, exist_ok=True)
        
        # Usunięcie starych plików (tylko 1 plik per user)
        for old_file in glob.glob(os.path.join(user_folder, '*.csv')):
            os.remove(old_file)
        
        # Zapis
        filepath = os.path.join(user_folder, filename)
        file.save(filepath)
```

### Co sprawdzamy:

- ✅ **Rozmiar**: max 16MB (config.py: `MAX_CONTENT_LENGTH`)
- ✅ **Rozszerzenie**: tylko `.csv` (WTForms: `FileAllowed`)
- ✅ **Bezpieczeństwo**: `secure_filename()` usuwa niebezpieczne znaki
- ✅ **Izolacja**: osobny folder per użytkownik

---

## 🔍 Etap 2: Detekcja formatu

### Kod: `app/services/csv_profile.py`

#### 2.1 Detekcja kodowania

```python
def _detect_encoding(data: bytes) -> str:
    """Wykrywa kodowanie pliku."""
    
    # UTF-8 z BOM (częste w polskich CSV z Excela)
    if data.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    
    # Próba UTF-8
    try:
        data.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        # Windows Polish (legacy)
        return "cp1250"
```

**Dlaczego to ważne?**
- 🇵🇱 Polskie znaki: ą, ć, ę, ł, ń, ó, ś, ź, ż
- 📊 Excel na Windows często zapisuje w CP1250
- 🌍 Nowoczesne systemy używają UTF-8

**Obsługiwane kodowania:**
1. `utf-8-sig` - UTF-8 z BOM (Excel Windows)
2. `utf-8` - Standard
3. `cp1250` - Windows Polish (legacy)

---

#### 2.2 Detekcja separatora (delimiter)

```python
def _detect_delimiter(text_sample: str) -> str:
    """Wykrywa separator kolumn."""
    
    try:
        # Użyj csv.Sniffer (wbudowany w Python)
        dialect = csv.Sniffer().sniff(
            text_sample, 
            delimiters=[",", ";", "\t", "|"]
        )
        return dialect.delimiter
    except Exception:
        # Fallback: wybierz najczęstszy
        lines = [ln for ln in text_sample.splitlines() if ln.strip()]
        first = lines[0]
        candidates = [",", ";", "\t", "|"]
        return max(candidates, key=lambda d: first.count(d))
```

**Obsługiwane separatory:**
- `,` (przecinek) - standard międzynarodowy
- `;` (średnik) - Excel PL (bo przecinek to separator dziesiętny)
- `\t` (tab) - TSV files
- `|` (pipe) - rzadziej używany

**Przykłady:**
```csv
# Przecinek
Name,Age,City
Jan,25,Warszawa

# Średnik
Nazwa;Wiek;Miasto
Jan;25;Warszawa

# Tab
Name    Age    City
Jan     25     Warszawa
```

---

#### 2.3 Detekcja nagłówków

```python
def _has_header(text_sample: str) -> bool:
    """Sprawdza czy CSV ma wiersz nagłówkowy."""
    try:
        return csv.Sniffer().has_header(text_sample)
    except Exception:
        return True  # zakładamy że jest
```

**Dlaczego to ważne?**
- Bez nagłówków trudno zrozumieć dane
- pandas domyślnie traktuje pierwszy wiersz jako header
- Nasze wykresy wymagają nazw kolumn

---

## 📊 Etap 3: Parsowanie

### Kod: `app/main/processing.py`

```python
def parse_and_validate_csv(path: str) -> pd.DataFrame:
    """Parsuje CSV i waliduje podstawowe wymagania."""
    
    # 1. Sprawdzenie czy plik istnieje
    if not Path(path).exists():
        raise CSVValidationError("CSV file does not exist")
    
    # 2. Sprawdzenie czy nie jest pusty
    if Path(path).stat().st_size == 0:
        raise CSVValidationError("CSV file is empty")
    
    # 3. Próba różnych separatorów
    ALLOWED_SEPARATORS = [",", ";", "\t"]
    best_df = None
    best_cols = -1
    
    for sep in ALLOWED_SEPARATORS:
        try:
            df = pd.read_csv(path, sep=sep, engine="python")
            if df.shape[1] > best_cols:
                best_df = df
                best_cols = df.shape[1]
        except Exception:
            continue
    
    if best_df is None:
        raise CSVValidationError("Unable to parse CSV")
    
    # 4. Walidacja wymiarów
    if best_df.shape[0] == 0:
        raise CSVValidationError("CSV has no rows")
    if best_df.shape[1] < 1:
        raise CSVValidationError("CSV has no columns")
    
    # 5. Czyszczenie nazw kolumn
    best_df.columns = [str(c).strip() for c in best_df.columns]
    
    return best_df
```

**Co sprawdzamy:**
- ✅ Plik istnieje
- ✅ Nie jest pusty
- ✅ Da się sparsować z któryms z separatorów
- ✅ Ma przynajmniej 1 wiersz i 1 kolumnę
- ✅ Nazwy kolumn są tekstowe

---

## 🧹 Etap 4: Czyszczenie danych

### 4.1 Normalizacja pustych wartości

#### Kod: `app/services/csv_profile.py`

```python
# Wczytanie z dtype=str (zachowanie wszystkich wartości)
df = pd.read_csv(
    BytesIO(data),
    encoding=encoding,
    sep=delimiter,
    dtype=str,
    keep_default_na=False  # nie zastępuj automatycznie
)

# Normalizacja: pusty string → pd.NA
df = df.applymap(
    lambda x: pd.NA if (x is None or 
                        (isinstance(x, str) and x.strip() == "")) 
              else x
)
```

**Dlaczego tak?**

CSV może mieć różne reprezentacje "braku danych":
```csv
Name,Age,City
Jan,25,Warszawa
Anna,,          # pusty string
Piotr,null,     # tekst "null"
Maria,NA,       # tekst "NA"
,30,Kraków      # brak wartości
```

**Nasza normalizacja:**
- Wszystko → pandas `pd.NA` (unified missing value)
- Ułatwia późniejszą detekcję braków
- Kompatybilne z pandas operations

---

### 4.2 Detekcja i konwersja liczb

#### Kod: `app/services/csv_profile.py`

```python
def _try_parse_numeric(s: pd.Series) -> Tuple[Optional[pd.Series], float]:
    """Próba konwersji na liczby. Obsługuje przecinek dziesiętny."""
    
    non_null = s.dropna().astype(str).str.strip()
    
    # Normalizacja:
    # "10 000,50" → "10000.50"
    # "10,5" → "10.5"
    # "10.5" → "10.5"
    normalized = (non_null
                  .str.replace(" ", "", regex=False)      # usuń spacje
                  .str.replace(",", ".", regex=False))    # przecinek → kropka
    
    # Konwersja
    parsed = pd.to_numeric(normalized, errors="coerce")
    success_ratio = parsed.notna().mean()
    
    # Jeśli >90% się udało → traktujemy jako numeric
    if success_ratio >= 0.9:
        return parsed, success_ratio
    else:
        return None, success_ratio
```

**Przykłady konwersji:**

```python
# Input (CSV)          # Output (pandas)
"10"         →         10.0
"10,5"       →         10.5
"10.5"       →         10.5
"10 000"     →         10000.0
"10 000,50"  →         10000.5
"1.5e3"      →         1500.0
"abc"        →         NaN (nie da się)
```

**Próg sukcesu: 90%**
- Jeśli ≥90% wartości da się przekonwertować → kolumna numeryczna
- Jeśli <90% → traktujemy jako tekst

---

### 4.3 Detekcja dat

#### Kod: `app/services/csv_profile.py`

```python
def _try_parse_datetime(s: pd.Series) -> Tuple[Optional[pd.Series], float]:
    """Próba parsowania dat. Obsługuje formaty ISO i day-first."""
    
    non_null = s.dropna().astype(str).str.strip()
    
    # Próba 1: ISO format (YYYY-MM-DD)
    parsed1 = pd.to_datetime(non_null, errors="coerce", utc=False)
    success1 = parsed1.notna().mean()
    
    # Próba 2: Day-first (DD-MM-YYYY) - częste w Polsce
    parsed2 = pd.to_datetime(non_null, errors="coerce", dayfirst=True, utc=False)
    success2 = parsed2.notna().mean()
    
    # Wybierz lepszy wynik
    best_success = max(success1, success2)
    
    if best_success >= 0.9:
        return (parsed1 if success1 >= success2 else parsed2), best_success
    else:
        return None, best_success
```

**Obsługiwane formaty dat:**

```python
# ISO format (YYYY-MM-DD)
"2024-01-15"
"2024-01-15 14:30:00"

# Day-first (DD-MM-YYYY) - polski standard
"15-01-2024"
"15.01.2024"
"15/01/2024"

# Month-first (MM-DD-YYYY) - USA
"01-15-2024"

# Tekstowe
"15 stycznia 2024"  # pandas potrafi!
"Jan 15, 2024"
```

**Próg sukcesu: 90%**
- Podobnie jak dla liczb
- Jeśli ≥90% to data, jeśli nie → tekst

---

### 4.4 Detekcja kodów (special case)

#### Kod: `app/services/csv_profile.py`

```python
def _is_probably_code_series(s: pd.Series) -> bool:
    """Czy kolumna to kody? (np. kody pocztowe, ID z zerami wiodącymi)"""
    
    non_null = s.dropna().astype(str).str.strip()
    
    # Case 1: Zera wiodące (np. "02", "007")
    if (non_null.str.match(r"^0\d+$")).any():
        return True
    
    # Case 2: Wszystkie cyfry, krótkie, stałej długości
    # (typowe dla kodów: 1-99, 001-999)
    if non_null.str.match(r"^\d+$").all():
        lengths = non_null.str.len()
        if lengths.max() <= 6 and lengths.nunique() <= 3:
            return True
    
    return False
```

**Dlaczego to ważne?**

```csv
# Kody pocztowe
Code,City
02-495,Warszawa  # zero wiodące!
30-001,Kraków
```

Gdybyśmy traktowali to jako liczby:
- `"02-495"` → błąd (myślnik)
- `"02"` → `2` (utrata zera!)

**Rozwiązanie:** Zostawiamy jako tekst (categorical)

---

### 4.5 Uzupełnianie braków danych

#### Kod: `app/main/processing.py`

```python
def basic_prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Przygotowanie danych do wizualizacji - uzupełnianie braków."""
    
    df = df.copy()
    
    # Kolumny numeryczne → uzupełnij medianą
    numeric_cols = df.select_dtypes(include="number").columns
    for col in numeric_cols:
        if df[col].isna().any():
            median_value = df[col].median()
            df[col] = df[col].fillna(median_value)
    
    # Kolumny tekstowe → uzupełnij "Brak danych"
    categorical_cols = df.select_dtypes(exclude="number").columns
    for col in categorical_cols:
        if df[col].isna().any():
            df[col] = df[col].fillna("Brak danych")
    
    return df
```

**Strategia uzupełniania:**

| Typ kolumny | Brak danych | Uzupełniamy |
|-------------|-------------|-------------|
| Numeryczna | `NaN` | **Mediana** |
| Kategoryczna | `NaN` | **"Brak danych"** |
| Data | `NaT` | (nie uzupełniamy) |

**Dlaczego mediana, a nie średnia?**

```python
# Przykład: ceny mieszkań
prices = [200k, 220k, 210k, 205k, 10M]  # jeden outlier!

mean(prices)   = 2.167M  # zła reprezentacja!
median(prices) = 210k    # dobra reprezentacja ✅
```

Mediana jest **odporna na outliery** (wartości odstające).

---

## 📈 Etap 5: Profilowanie kolumn

### Kod: `app/services/csv_profile.py`

```python
def profile_csv_upload(file_obj) -> CsvProfileResult:
    """Główna funkcja - profilowanie przesłanego CSV."""
    
    # ... (parsowanie, detekcja formatu)
    
    dimensions = []     # kolumny kategoryczne
    measures = []       # kolumny numeryczne
    datetimes = []      # kolumny dat
    
    for col in df.columns:
        s = df[col]
        
        # Sprawdź czy kod
        if _is_probably_code_series(s):
            inferred_type = "string"
            semantic_type = "categorical"
            dimensions.append(col)
        
        else:
            # Próba: data
            parsed_dt, dt_ratio = _try_parse_datetime(s)
            if parsed_dt is not None:
                inferred_type = "date"
                semantic_type = "datetime"
                datetimes.append(col)
            
            else:
                # Próba: liczba
                parsed_num, num_ratio = _try_parse_numeric(s)
                if parsed_num is not None:
                    inferred_type = "numeric"
                    semantic_type = "measure"
                    measures.append(col)
                
                else:
                    # Fallback: tekst
                    inferred_type = "string"
                    semantic_type = "categorical"
                    dimensions.append(col)
        
        # Statystyki kolumny
        schema_cols.append({
            "name": col,
            "inferred_type": inferred_type,
            "semantic_type": semantic_type,
            "missing_count": int(s.isna().sum()),
            "unique_count": int(s.dropna().nunique()),
            # ... więcej metadanych
        })
    
    return CsvProfileResult(
        meta={...},
        schema={
            "columns": schema_cols,
            "suggestions": {
                "dimensions": dimensions,    # do group-by
                "measures": measures,         # do agregacji
                "datetimes": datetimes       # do osi czasu
            }
        },
        preview={...}
    )
```

**Wynik profilowania:**

```json
{
  "schema": {
    "columns": [
      {
        "name": "Product",
        "inferred_type": "string",
        "semantic_type": "categorical",
        "missing_count": 2,
        "unique_count": 5
      },
      {
        "name": "Price",
        "inferred_type": "numeric",
        "semantic_type": "measure",
        "missing_count": 1,
        "unique_count": 15,
        "stats": {"min": 10.5, "max": 99.9, "mean": 45.2}
      },
      {
        "name": "Date",
        "inferred_type": "date",
        "semantic_type": "datetime",
        "missing_count": 0,
        "unique_count": 10
      }
    ],
    "suggestions": {
      "dimensions": ["Product", "Category"],
      "measures": ["Price", "Quantity"],
      "datetimes": ["Date"]
    }
  }
}
```

**Zastosowanie:**
- Frontend wie, które kolumny można sumować
- Frontend wie, które kolumny pokazać w group-by
- Automatyczne sugestie wykresów

---

## 📊 Etap 6: Przygotowanie do wizualizacji

### 6.1 Statystyki

#### Kod: `app/main/processing.py`

```python
def compute_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    """Oblicza statystyki dla całego datasetu."""
    
    rows, cols = df.shape
    missing_total = int(df.isna().sum().sum())
    
    numeric_columns = []
    numeric_summary = {}
    
    for col in df.columns:
        series = df[col]
        coerced = pd.to_numeric(series, errors="coerce")
        
        if coerced.notna().any():
            numeric_columns.append(col)
            
            numeric_summary[col] = {
                "min": float(coerced.min()),
                "max": float(coerced.max()),
                "mean": float(coerced.mean()),
                "missing": int(coerced.isna().sum()),
            }
    
    return {
        "rows": int(rows),
        "cols": int(cols),
        "columns": list(df.columns),
        "missing_total": missing_total,
        "numeric_columns": numeric_columns,
        "numeric_summary": numeric_summary,
    }
```

**Przykład wyniku:**

```json
{
  "rows": 100,
  "cols": 5,
  "columns": ["Product", "Price", "Quantity", "Date", "City"],
  "missing_total": 12,
  "numeric_columns": ["Price", "Quantity"],
  "numeric_summary": {
    "Price": {
      "min": 10.5,
      "max": 99.9,
      "mean": 45.23,
      "missing": 3
    },
    "Quantity": {
      "min": 1.0,
      "max": 100.0,
      "mean": 25.5,
      "missing": 5
    }
  }
}
```

---

### 6.2 Filtrowanie danych

#### Kod: `app/main/plotly_charts.py`

```python
def _apply_filters(
    df: pd.DataFrame,
    filter_column: str | None = None,
    filter_min: float | None = None,
    filter_max: float | None = None,
    filter_values: list[str] | None = None,
    filter_op: str | None = None,
    filter_value: str | None = None,
) -> pd.DataFrame:
    """Filtruje dane przed wizualizacją."""
    
    if not filter_column:
        return df
    
    s = df[filter_column]
    
    # Filtr numeryczny: zakres
    if pd.api.types.is_numeric_dtype(s):
        out = df
        if filter_min is not None:
            out = out[out[filter_column] >= filter_min]
        if filter_max is not None:
            out = out[out[filter_column] <= filter_max]
        return out
    
    # Filtr kategoryczny: lista wartości
    if filter_values:
        return df[df[filter_column].astype(str).isin(filter_values)]
    
    # Filtr tekstowy: contains/equals
    if filter_op and filter_value:
        st = s.astype(str)
        if filter_op == "contains":
            return df[st.str.contains(filter_value, case=False, na=False)]
        if filter_op == "equals":
            return df[st == filter_value]
    
    return df
```

**Przykłady użycia:**

```python
# Filtr numeryczny
df_filtered = _apply_filters(
    df,
    filter_column="Price",
    filter_min=20.0,
    filter_max=50.0
)
# Wynik: tylko produkty 20-50 PLN

# Filtr kategoryczny
df_filtered = _apply_filters(
    df,
    filter_column="City",
    filter_values=["Warszawa", "Kraków"]
)
# Wynik: tylko 2 miasta

# Filtr tekstowy
df_filtered = _apply_filters(
    df,
    filter_column="Product",
    filter_op="contains",
    filter_value="laptop"
)
# Wynik: produkty zawierające "laptop"
```

---

### 6.3 Generowanie wykresów

#### Kod: `app/main/plotly_charts.py`

```python
def bar_counts(
    df: pd.DataFrame,
    column: str,
    top_n: int = 20,
    **filters
) -> dict:
    """Wykres słupkowy liczności kategorii."""
    
    # 1. Filtruj dane
    df_f = _apply_filters(df, **filters)
    
    # 2. Policz wartości
    counts = (df_f[column]
              .astype(str)
              .value_counts(dropna=False)
              .head(top_n)
              .sort_values(ascending=True))  # poziomy wykres
    
    # 3. Przygotuj DataFrame
    cdf = counts.reset_index()
    cdf.columns = [column, "count"]
    
    # 4. Generuj wykres Plotly
    fig = px.bar(
        cdf,
        x="count",
        y=column,
        orientation="h",  # horizontal
        title=f"Liczności: {column} (top {top_n})",
    )
    
    # 5. Zwróć jako JSON
    return json.loads(pio.to_json(fig))
```

**Inne wykresy:**
- `histogram()` - rozkład wartości numerycznych
- `boxplot()` - kwartyle, outliery
- `scatter()` - korelacja x vs y
- `corr_heatmap()` - macierz korelacji

---

## 🐛 Problemy i rozwiązania

### Problem 1: Polskie znaki (ą, ć, ę...)

**Symptom:**
```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb1
```

**Przyczyna:**
- Windows Excel zapisuje w CP1250
- Python domyślnie próbuje UTF-8

**Rozwiązanie:**
```python
def _detect_encoding(data: bytes) -> str:
    # Próba UTF-8
    try:
        data.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "cp1250"  # fallback
```

---

### Problem 2: Średnik jako separator

**Symptom:**
```csv
Name;Age;City
Jan;25;Warszawa
```
Pandas traktuje jako 1 kolumnę: `"Name;Age;City"`

**Przyczyna:**
- W Polsce Excel używa `;` (bo `,` to separator dziesiętny)
- pandas domyślnie zakłada `,`

**Rozwiązanie:**
```python
# Automatyczna detekcja
delimiter = _detect_delimiter(text_sample)
df = pd.read_csv(file, sep=delimiter)
```

---

### Problem 3: Przecinek dziesiętny

**Symptom:**
```csv
Price
10,5   # chcemy 10.5, nie tekst "10,5"
```

**Przyczyna:**
- Polski standard: `10,5`
- Python/pandas oczekuje: `10.5`

**Rozwiązanie:**
```python
normalized = s.str.replace(",", ".", regex=False)
parsed = pd.to_numeric(normalized, errors="coerce")
```

---

### Problem 4: Zera wiodące w kodach

**Symptom:**
```csv
PostalCode
02-495    # po konwersji na int: 2495 (utrata zera!)
```

**Rozwiązanie:**
```python
if _is_probably_code_series(s):
    # Zostaw jako string
    inferred_type = "string"
```

---

### Problem 5: Różne reprezentacje brakujących danych

**Symptom:**
```csv
Name,Age
Jan,25
Anna,      # pusty
Piotr,null # tekst "null"
Maria,NA   # tekst "NA"
```

**Rozwiązanie:**
```python
# Normalizacja wszystkich → pd.NA
df = df.applymap(
    lambda x: pd.NA if (x is None or 
                        (isinstance(x, str) and x.strip() == ""))
              else x
)
```

---

### Problem 6: Duplikaty nazw kolumn

**Symptom:**
```csv
Name,Age,Name    # duplikat!
Jan,25,Kowalski
```

**Rozwiązanie:**
```python
# Automatyczne dodanie sufiksów
seen = {}
new_cols = []
for c in cols:
    if c not in seen:
        seen[c] = 1
        new_cols.append(c)
    else:
        seen[c] += 1
        new_cols.append(f"{c}__{seen[c]}")  # Name__2

df.columns = new_cols
```

---

## 💡 Przykłady end-to-end

### Przykład 1: Plik z polskimi znakami

**Input: `sprzedaz.csv` (CP1250, średnik)**
```csv
Produkt;Cena;Ilość;Miasto
Laptop;2500,50;10;Warszawa
Mysz;45,99;100;Kraków
Klawiatura;;50;Gdańsk
```

**Pipeline:**
1. ✅ Detekcja: CP1250, separator=`;`
2. ✅ Parsowanie: 4 kolumny, 3 wiersze
3. ✅ Czyszczenie:
   - `"2500,50"` → `2500.5`
   - `""` (pusta cena) → `pd.NA`
   - `"Gdańsk"` (polskie znaki) → OK
4. ✅ Profilowanie:
   - `Produkt`: categorical
   - `Cena`: numeric (brak: 1)
   - `Ilość`: numeric
   - `Miasto`: categorical
5. ✅ Uzupełnianie:
   - Cena: `pd.NA` → `1273.245` (mediana)
6. ✅ Wizualizacja: wykresy gotowe!

---

### Przykład 2: Plik z datami

**Input: `zamowienia.csv`**
```csv
Data,Produkt,Wartość
2024-01-15,Laptop,2500
15.01.2024,Mysz,45.99
2024-01-16,Klawiatura,199
```

**Pipeline:**
1. ✅ Detekcja dat:
   - Próba 1 (ISO): 66% sukces
   - Próba 2 (day-first): 100% sukces ✅
2. ✅ Konwersja:
   - `"2024-01-15"` → datetime
   - `"15.01.2024"` → datetime (ten sam!)
3. ✅ Profilowanie:
   - `Data`: datetime
   - `Produkt`: categorical
   - `Wartość`: numeric
4. ✅ Sugestia: wykres liniowy (oś X = Data)

---

### Przykład 3: Plik z kodami pocztowymi

**Input: `adresy.csv`**
```csv
KodPocztowy,Miasto
02-495,Warszawa
30-001,Kraków
01,Warszawa
```

**Bez detekcji kodów:**
- `"02-495"` → błąd parsowania (myślnik)
- `"01"` → `1` (utrata zera!)

**Z detekcją kodów:**
1. ✅ `_is_probably_code_series()` wykrywa zera wiodące
2. ✅ Kolumna traktowana jako `string`
3. ✅ Wartości zachowane: `"02-495"`, `"01"`

---

## 📚 Biblioteki i narzędzia

### pandas
```python
import pandas as pd

# Core operations
pd.read_csv()           # parsowanie
pd.to_numeric()         # konwersja liczb
pd.to_datetime()        # konwersja dat
df.fillna()             # uzupełnianie braków
df.isna()               # detekcja braków
df.select_dtypes()      # filtrowanie po typie
```

### Plotly
```python
import plotly.express as px
import plotly.io as pio

# Wykresy
px.bar()                # wykres słupkowy
px.histogram()          # histogram
px.box()                # boxplot
px.scatter()            # scatter plot
px.imshow()             # heatmapa

# Serializacja
pio.to_json()           # figura → JSON
```

### Python stdlib
```python
import csv

csv.Sniffer()           # detekcja separatora
.sniff()                # detekcja dialektu
.has_header()           # czy ma nagłówki
```

---

## 🎯 Podsumowanie procesu

### Co robimy dobrze ✅

1. **Automatyczna detekcja formatu**
   - Kodowanie, separator, nagłówki
   - Działa z różnymi źródłami

2. **Robustne parsowanie**
   - Obsługa polskich znaków
   - Obsługa różnych separatorów
   - Graceful degradation

3. **Inteligentna detekcja typów**
   - Liczby (z przecinkiem)
   - Daty (różne formaty)
   - Kody (zachowanie zer)

4. **Sensowne czyszczenie**
   - Mediana dla liczb (odporna na outliery)
   - "Brak danych" dla tekstu
   - Normalizacja braków

5. **Metadane dla frontendu**
   - Sugestie kolumn do wykresów
   - Statystyki
   - Podgląd danych

### Co można poprawić 💡

1. **Więcej strategii uzupełniania**
   - Interpolacja dla szeregów czasowych
   - KNN imputation
   - Forward/backward fill

2. **Detekcja outlierów**
   - Z-score
   - IQR method
   - Isolation Forest

3. **Walidacja logiczna**
   - Wiek >0 i <150
   - Cena >0
   - Data nie w przyszłości

4. **Profilowanie zaawansowane**
   - Korelacje między kolumnami
   - Analiza rozkładów
   - Wykrywanie anomalii

---

**Dokument stworzony:** 28 stycznia 2026  
**Wersja:** 1.0  
**Autorzy:** Zespół WSB Data Charts

