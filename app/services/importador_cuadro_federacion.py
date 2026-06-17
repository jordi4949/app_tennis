import re
from typing import Any


DATE_PATTERN = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+DE\s+[A-ZÀ-Ü]+(?:\s+DE)?\s+\d{4})\b",
    re.IGNORECASE,
)
RESULT_PATTERN = re.compile(
    r"\b(?:\d{1,2}[-/]\d{1,2}(?:\s*\(\d{1,2}[-/]\d{1,2}\))?|WO|W\.O\.|RET|BYE)\b",
    re.IGNORECASE,
)


def importar_pdf_cuadro_federacion(pdf_bytes: bytes) -> dict[str, Any]:
    """Extracts a first-pass bracket summary from a Catalan federation PDF."""
    try:
        import fitz
    except ImportError:
        return {
            "ok": False,
            "error": "PyMuPDF no está instalado. Instala la dependencia 'pymupdf'.",
            "cabecera": {},
            "ronda_1": [],
            "paginas": [],
        }

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    paginas = []

    for page_index, page in enumerate(doc, start=1):
        text = page.get_text("text")
        words = page.get_text("words")
        lines = _normalizar_lineas(text)

        paginas.append({
            "pagina": page_index,
            "texto": text,
            "lineas": lines,
            "words": words,
        })

    all_lines = [line for pagina in paginas for line in pagina["lineas"]]
    cabecera = _extraer_cabecera(all_lines)
    ronda_1 = []

    for pagina in paginas:
        ronda_1.extend(_extraer_ronda_1_desde_words(pagina["words"]))

    if not ronda_1:
        ronda_1 = _extraer_ronda_1_desde_lineas(all_lines)

    return {
        "ok": True,
        "metodo": "pymupdf_texto_directo",
        "cabecera": cabecera,
        "ronda_1": ronda_1,
        "resumen": {
            "paginas": len(paginas),
            "lineas_extraidas": len(all_lines),
            "entradas_ronda_1": len(ronda_1),
        },
        "texto_preview": all_lines[:80],
    }


def _normalizar_lineas(text: str) -> list[str]:
    return [
        re.sub(r"\s+", " ", line).strip()
        for line in text.splitlines()
        if line.strip()
    ]


def _extraer_cabecera(lines: list[str]) -> dict[str, Any]:
    header_lines = _lineas_antes_de_rondas(lines)
    modalidad = _buscar_modalidad(lines)
    fechas = _buscar_fechas(lines)

    return {
        "torneo": _buscar_torneo(header_lines),
        "fechas": fechas,
        "club": _buscar_club(header_lines),
        "modalidad_categoria_genero_cuadro": modalidad,
        "lineas_cabecera": header_lines[:25],
    }


def _lineas_antes_de_rondas(lines: list[str]) -> list[str]:
    header = []
    for line in lines:
        if _es_cabecera_ronda(line):
            break
        header.append(line)
    return header


def _buscar_torneo(lines: list[str]) -> str | None:
    for line in lines:
        upper = line.upper()
        if any(token in upper for token in ("TORNEIG", "TORNEO", "CAMPIONAT", "CIRCUIT", "COPA")):
            return line

    for line in lines:
        upper = line.upper()
        if not DATE_PATTERN.search(line) and "CLUB" not in upper and len(line) > 8:
            return line

    return None


def _buscar_fechas(lines: list[str]) -> list[str]:
    fechas = []
    for line in lines:
        fechas.extend(match.group(0) for match in DATE_PATTERN.finditer(line))
    return fechas


def _buscar_club(lines: list[str]) -> str | None:
    for line in lines:
        upper = line.upper()
        if any(token in upper for token in ("CLUB", "C.T.", " CT ", "RCT", "TENNIS", "TENIS")):
            return line
    return None


def _buscar_modalidad(lines: list[str]) -> str | None:
    for line in lines:
        upper = line.upper()
        if "QUADRE" in upper or "CUADRO" in upper:
            return line
    for line in lines:
        upper = line.upper()
        if any(token in upper for token in ("INDIVIDUAL", "MASCULINO", "FEMENINO", "FEMENI", "MASCULI", "SUB-")):
            return line
    return None


def _es_cabecera_ronda(line: str) -> bool:
    upper = line.upper()
    return bool(re.search(r"\bRONDA\s*1\b", upper)) or "SEMIFINAL" in upper or "FINAL" == upper


def _extraer_ronda_1_desde_words(words: list[tuple]) -> list[dict[str, Any]]:
    if not words:
        return []

    headers = []
    for index, word in enumerate(words):
        text = str(word[4]).upper()
        if text == "RONDA":
            next_text = str(words[index + 1][4]).upper() if index + 1 < len(words) else ""
            if next_text == "1":
                headers.append(_merge_word_boxes([word, words[index + 1]]))
        elif text in {"RONDA1", "RONDA", "1"} and "RONDA 1" in " ".join(str(w[4]).upper() for w in words[index:index + 2]):
            headers.append(_merge_word_boxes([word]))

    if not headers:
        return []

    header = sorted(headers, key=lambda item: item["x0"])[0]
    next_header_x = _buscar_siguiente_cabecera_x(words, header["x0"])
    x0 = max(header["x0"] - 30, 0)
    x1 = next_header_x if next_header_x else header["x0"] + 260
    y0 = header["y1"]

    column_words = [
        word
        for word in words
        if word[0] >= x0 and word[0] < x1 and word[1] > y0
    ]

    grouped_lines = _agrupar_words_por_linea(column_words)
    return [_parsear_linea_ronda_1(line, pos + 1) for pos, line in enumerate(grouped_lines)]


def _buscar_siguiente_cabecera_x(words: list[tuple], current_x: float) -> float | None:
    candidates = []
    for index, word in enumerate(words):
        text = str(word[4]).upper()
        if text == "RONDA":
            next_text = str(words[index + 1][4]).upper() if index + 1 < len(words) else ""
            if next_text.isdigit() and int(next_text) > 1:
                candidates.append(word[0])
        elif text in {"SEMIFINAL", "FINAL"}:
            candidates.append(word[0])

    candidates = [x for x in candidates if x > current_x + 20]
    return min(candidates) if candidates else None


def _merge_word_boxes(words: list[tuple]) -> dict[str, float]:
    return {
        "x0": min(word[0] for word in words),
        "y0": min(word[1] for word in words),
        "x1": max(word[2] for word in words),
        "y1": max(word[3] for word in words),
    }


def _agrupar_words_por_linea(words: list[tuple]) -> list[str]:
    sorted_words = sorted(words, key=lambda item: (round(item[1] / 4) * 4, item[0]))
    rows: list[list[tuple]] = []

    for word in sorted_words:
        y = word[1]
        for row in rows:
            if abs(row[0][1] - y) <= 4:
                row.append(word)
                break
        else:
            rows.append([word])

    lines = []
    for row in rows:
        text = " ".join(str(word[4]) for word in sorted(row, key=lambda item: item[0]))
        text = re.sub(r"\s+", " ", text).strip()
        if text and not _es_cabecera_ronda(text):
            lines.append(text)

    return lines


def _extraer_ronda_1_desde_lineas(lines: list[str]) -> list[dict[str, Any]]:
    start = None
    for index, line in enumerate(lines):
        if re.search(r"\bRONDA\s*1\b", line, re.IGNORECASE):
            start = index + 1
            break

    if start is None:
        return []

    extracted = []
    for line in lines[start:]:
        if re.search(r"\bRONDA\s*[2-9]\b|SEMIFINAL|FINAL", line, re.IGNORECASE):
            break
        extracted.append(_parsear_linea_ronda_1(line, len(extracted) + 1))

    return extracted


def _parsear_linea_ronda_1(line: str, fallback_position: int) -> dict[str, Any]:
    clean = re.sub(r"\s+", " ", line).strip()
    position = fallback_position

    position_match = re.match(r"^(\d{1,3})[\s\.-]+(.+)$", clean)
    if position_match:
        position = int(position_match.group(1))
        clean = position_match.group(2).strip()

    resultados = [match.group(0) for match in RESULT_PATTERN.finditer(clean)]
    jugador = RESULT_PATTERN.sub(" ", clean)
    jugador = re.sub(r"\bBYE\b", " ", jugador, flags=re.IGNORECASE)
    jugador = re.sub(r"\s+", " ", jugador).strip(" -")

    es_bye = "BYE" in clean.upper()

    return {
        "posicion": position,
        "jugador_detectado": None if es_bye and not jugador else jugador,
        "bye": es_bye,
        "resultado_detectado": " ".join(resultados) if resultados else None,
        "texto_original": line,
        "confianza": _confianza_linea(jugador, es_bye, resultados),
    }


def _confianza_linea(jugador: str, es_bye: bool, resultados: list[str]) -> str:
    if es_bye:
        return "alta"
    if jugador and resultados:
        return "media"
    if jugador:
        return "media"
    return "baja"
