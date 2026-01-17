import pandas as pd

# IMPORT OLD ALL-IN-ONE CHECKER (AUTHORITATIVE LOGIC)
from checker_logic_old import validate_catalog_file as old_all_in_one_checker


# ---------- COMMON HELPERS ---------- #

def _norm_str(v):
    if pd.isna(v) or v is None:
        return ""
    return str(v).strip()


def _parse_float(v):
    try:
        clean = str(v).replace("%", "").strip()
        return float(clean) if clean else 0.0
    except:
        return 0.0


def _is_empty(v):
    return _norm_str(v) == ""


def _find_col(df, keywords):
    for col in df.columns:
        name = str(col).upper()
        if all(k.upper() in name for k in keywords):
            return col
    return None


# ---------- MODULAR CHECKS ---------- #

def check_multiline_metadata(row, row_num, df):
    """
    Validates Alternate Title lines against AKA {i} 
    and Artist(s) lines against Recording Display Artist {i}
    """
    errs = []

    # 1. Validation for Alternate Title -> AKA 1, AKA 2...
    col_alt_source = _find_col(df, ["ALTERNATE", "TITLE"])
    if col_alt_source:
        raw_val = _norm_str(row.get(col_alt_source))
        if raw_val:
            # Split by newline and remove empty lines
            lines = [line.strip() for line in raw_val.split('\n') if line.strip()]
            for i, line_text in enumerate(lines, 1):
                # Search specifically for "AKA" and the index number
                col_aka = _find_col(df, ["AKA", str(i)])
                if col_aka:
                    aka_val = _norm_str(row.get(col_aka))
                    if aka_val.upper() != line_text.upper():
                        errs.append(f"Row {row_num}: Alternate Title line {i} does not match {col_aka}")
                else:
                    errs.append(f"Row {row_num}: Column 'AKA {i}' not found to match Alternate Title line {i}")

    # 2. Validation for Artist(s) -> Recording Display Artist 1, 2...
    col_art_source = _find_col(df, ["ARTIST(S)"])
    if col_art_source:
        raw_val = _norm_str(row.get(col_art_source))
        if raw_val:
            lines = [line.strip() for line in raw_val.split('\n') if line.strip()]
            for i, line_text in enumerate(lines, 1):
                col_art_target = _find_col(df, ["RECORDING", "DISPLAY", "ARTIST", str(i)])
                if col_art_target:
                    target_val = _norm_str(row.get(col_art_target))
                    if target_val.upper() != line_text.upper():
                        errs.append(f"Row {row_num}: Artist line {i} does not match {col_art_target}")
                else:
                    errs.append(f"Row {row_num}: Column 'Recording Display Artist {i}' not found to match Artist line {i}")

    return errs


def check_iswc_only(row, row_num, col_iswc):
    errs = []
    val = _norm_str(row.get(col_iswc))
    if "." in val or "NOTES" in val.upper():
        errs.append(f"Row {row_num}: ISWC has dots or Notes")
    return errs


def check_release_info_only(row, row_num, cols):
    errs = []

    isrc = _norm_str(row.get(cols["isrc"]))
    rel_link = _norm_str(row.get(cols["rel_link"]))

    if isrc:
        if _is_empty(row.get(cols["rel_date"])):
            errs.append(f"Row {row_num}: Recording Release Date (CWR) is missing or not matched")
        if _is_empty(row.get(cols["rec_title"])):
            errs.append(f"Row {row_num}: Recording Title is missing or not matched")
        if _is_empty(row.get(cols["upc"])):
            errs.append(f"Row {row_num}: Album UPC is missing or not matched")
        if _is_empty(rel_link):
            errs.append(f"Row {row_num}: Release Link is missing or not matched")

    if rel_link and not isrc:
        errs.append(f"Row {row_num}: Recording ISRC is missing or not matched (Required for Release Link)")

    if rel_link and _is_empty(row.get(cols["portal_link"])):
        errs.append(f"Row {row_num}: PORTAL LINK TO SONG is missing or not matched")

    return errs


def check_dropdown_only(row, row_num, df):
    errs = []

    col_writer_total = _find_col(df, ["WRITER", "TOTAL"])
    wt_raw = row.get(col_writer_total)

    if _is_empty(wt_raw):
        errs.append(f"Row {row_num}: Writer Total is missing or not matched")
        return errs

    try:
        w_count = int(float(wt_raw))
    except:
        errs.append(f"Row {row_num}: Writer Total is not a valid number")
        return errs

    loop_limit = min(w_count, 20)
    total_share = 0.0

    for i in range(1, loop_limit + 1):
        c_share_col = _find_col(df, [f"COMPOSER {i}", "SHARE"])
        c_ctrl_col = _find_col(df, [f"COMPOSER {i}", "CONTROLLED"])
        c_cap_col = _find_col(df, [f"COMPOSER {i}", "CAPACITY"])
        c_link_col = _find_col(df, [f"COMPOSER {i}", "LINKED", "PUBLISHER"])

        p_name_col = _find_col(df, [f"PUBLISHER {i}", "NAME"])
        p_cae_col = _find_col(df, [f"PUBLISHER {i}", "CAE"])
        p_aff_col = _find_col(df, [f"PUBLISHER {i}", "AFFILIATION"])
        p_cap_col = _find_col(df, [f"PUBLISHER {i}", "CAPACITY"])
        p_share_col = _find_col(df, [f"PUBLISHER {i}", "SHARE"])

        raw_share = row.get(c_share_col)
        if _is_empty(raw_share):
            errs.append(f"Row {row_num}: Composer {i} Share is missing or not matched")
            share_val = 0.0
        else:
            share_val = _parse_float(raw_share)

        total_share += share_val

        if _norm_str(row.get(c_ctrl_col)).upper() not in ["Y", "N"]:
            errs.append(f"Row {row_num}: Composer {i} Controlled is missing or not matched")

        if _norm_str(row.get(c_cap_col)).upper() not in ["A", "C", "AC", "CA"]:
            errs.append(f"Row {row_num}: Composer {i} Capacity is missing or not matched")

        link_val = _norm_str(row.get(c_link_col))
        if not link_val:
            errs.append(f"Row {row_num}: Composer {i} Linked Publisher is missing or not matched")

        pub_name = _norm_str(row.get(p_name_col)).upper()
        pub_cae = _norm_str(row.get(p_cae_col)).replace(".0", "")
        pub_aff = _norm_str(row.get(p_aff_col)).upper()

        if link_val.upper() == "ELITE EMBASSY PUBLISHING":
            if pub_name != "ELITE EMBASSY PUBLISHING":
                errs.append(f"Row {row_num}: Publisher {i} Name is missing or not matched")
            if pub_cae != "619851030":
                errs.append(f"Row {row_num}: Publisher {i} CAE No is missing or not matched")
            if pub_aff != "BMI":
                errs.append(f"Row {row_num}: Publisher {i} Affiliation is missing or not matched")

        if _norm_str(row.get(p_cap_col)).upper() != "OP":
            errs.append(f"Row {row_num}: Publisher {i} Capacity is missing or not matched (Should be OP)")

        pub_share = _parse_float(row.get(p_share_col))
        if _is_empty(row.get(p_share_col)) or abs(pub_share - share_val) > 0.01:
            errs.append(f"Row {row_num}: Publisher {i} Share does not match Composer {i} Share")

    if abs(total_share - 100.0) > 0.1:
        errs.append(f"Row {row_num}: Total Share is not 100%")

    return errs


# ---------- MAIN ENTRY POINT ---------- #

def validate_catalog_file(file_buffer, check_mode="ALL IN ONE"):

    if check_mode == "ALL IN ONE":
        # Note: You might want to update the old checker too if you want 
        # these new rules to appear in 'ALL IN ONE' mode.
        return old_all_in_one_checker(file_buffer)

    df = pd.read_excel(file_buffer)

    cols = {
        "catalog": _find_col(df, ["EEP", "CATALOG"]),
        "title": _find_col(df, ["TITLE"]),
        "iswc": _find_col(df, ["ISWC"]),
        "isrc": _find_col(df, ["RECORDING", "ISRC"]),
        "rel_date": _find_col(df, ["RELEASE", "DATE", "CWR"]),
        "rec_title": _find_col(df, ["RECORDING", "TITLE"]),
        "upc": _find_col(df, ["ALBUM", "UPC"]),
        "rel_link": next((c for c in df.columns if str(c).upper().strip() == "RELEASE LINK"), None),
        "portal_link": _find_col(df, ["PORTAL", "LINK"]),
    }

    errors = []

    for idx, row in df.iterrows():
        row_num = idx + 2
        cid = _norm_str(row.get(cols["catalog"])) or "Unknown ID"
        title = _norm_str(row.get(cols["title"])) or "Unknown Title"

        issues = []

        if check_mode == "ISWC" and cols["iswc"]:
            issues += check_iswc_only(row, row_num, cols["iswc"])

        if check_mode == "RELEASE INFO":
            issues += check_release_info_only(row, row_num, cols)

        if check_mode == "DROPDOWN":
            issues += check_dropdown_only(row, row_num, df)
            
        # ADDED: New metadata mode
        if check_mode == "METADATA":
            issues += check_multiline_metadata(row, row_num, df)

        for msg in issues:
            errors.append({
                "ID": cid,
                "Title": title,
                "Issue": msg
            })

    return errors