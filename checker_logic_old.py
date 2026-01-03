import pandas as pd
import math

def _norm_str(val):
    """Normalize string: trim, upper, handle None."""
    if pd.isna(val) or val is None:
        return ""
    return str(val).strip()

def _parse_float(val):
    """Parse numeric values safely."""
    if pd.isna(val) or val is None or val == "":
        return 0.0
    try:
        s = str(val).replace("%", "").strip()
        return float(s)
    except:
        return 0.0

def _is_empty(val):
    """Check if value is effectively empty."""
    return _norm_str(val) == ""

def _find_col(df, keywords):
    """Find column using fuzzy matching."""
    for col in df.columns:
        c_upper = str(col).upper().strip()
        if all(k.upper() in c_upper for k in keywords):
            return col
    return None

def validate_catalog_file(file_buffer):
    # Exclusion List
    EXCLUSIONS = ["NRY", "NRYI", "YTO", "UATF", "UATFOS"]
    
    try:
        df = pd.read_excel(file_buffer)
    except Exception as e:
        return [{"ID": "N/A", "Title": "N/A", "Issue": f"System Error: Could not read Excel file. {str(e)}"}]

    errors = []

    # --- Identify Columns (Fuzzy Search) ---
    col_catalog = _find_col(df, ["EEP", "MASTER", "CATALOG"])
    col_title = _find_col(df, ["TITLE"])
    col_iswc = _find_col(df, ["ISWC"])
    
    # Release Details Columns
    col_isrc = _find_col(df, ["RECORDING", "ISRC"])
    col_release_date = _find_col(df, ["RECORDING", "RELEASE", "DATE", "CWR"])
    col_rec_title = _find_col(df, ["RECORDING", "TITLE"])
    col_upc = _find_col(df, ["ALBUM", "UPC"])
    col_release_link = _find_col(df, ["RELEASE", "LINK"])
    col_portal_link = _find_col(df, ["PORTAL", "LINK"])
    
    col_writer_total = _find_col(df, ["WRITER", "TOTAL"])

    for idx, row in df.iterrows():
        row_num = idx + 2 # Excel Row Number
        
        # --- Identification Data ---
        cat_val = _norm_str(row.get(col_catalog)) if col_catalog else "Unknown ID"
        title_val = _norm_str(row.get(col_title)) if col_title else "Unknown Title"
        
        def add_err(msg):
            errors.append({
                "ID": cat_val,
                "Title": title_val,
                "Issue": f"Row {row_num}: {msg}"
            })

        # --- Exclusion Check Helper ---
        def is_excluded(val):
            val_norm = _norm_str(val).upper()
            return any(exc in val_norm for exc in EXCLUSIONS)

        # --- ISWC Check ---
        if col_iswc:
            iswc_val = _norm_str(row.get(col_iswc))
            if not is_excluded(iswc_val):
                if "." in iswc_val or "NOTES" in iswc_val.upper():
                    add_err("ISWC has dots or Notes")

        # --- ISRC & Release Details ---
        isrc_val = _norm_str(row.get(col_isrc)) if col_isrc else ""
        rec_title_val = _norm_str(row.get(col_rec_title)) if col_rec_title else ""
        rel_link_val = _norm_str(row.get(col_release_link)) if col_release_link else ""

        has_isrc = not _is_empty(isrc_val)
        has_rel_link = not _is_empty(rel_link_val)

        # Rule: If ISRC is available -> Check Song Release Details
        # Skip these if ISRC, Rec Title, or Release Link contains an exclusion
        if has_isrc and not any(is_excluded(v) for v in [isrc_val, rec_title_val, rel_link_val]):
            if col_release_date and _is_empty(row.get(col_release_date)):
                add_err("Recording Release Date (CWR) is missing or not matched")
            
            if col_rec_title and _is_empty(row.get(col_rec_title)):
                add_err("Recording Title is missing or not matched")

            if col_upc and _is_empty(row.get(col_upc)):
                add_err("Album UPC is missing or not matched")

            if col_release_link and _is_empty(rel_link_val):
                add_err("Release Link is missing or not matched")

        # Rule: Release Link Logic (Skip if exclusion found)
        if has_rel_link and not is_excluded(rel_link_val):
            if not has_isrc:
                 add_err("Recording ISRC is missing or not matched (Required for Release Link)")
            
            if col_portal_link and _is_empty(row.get(col_portal_link)):
                add_err("PORTAL LINK TO SONG is missing or not matched")

        # --- Writers Section ---
        # (Writers logic remains strict as per original code unless specified otherwise)
        total_share = 0.0
        w_total_val = row.get(col_writer_total) if col_writer_total else 0
        w_count = 0
        
        if _is_empty(w_total_val):
            add_err("Writer Total is missing or not matched")
        else:
            try:
                w_count = int(float(w_total_val))
            except:
                 add_err("Writer Total is not a valid number")

        loop_limit = min(w_count, 20)
        
        for i in range(1, loop_limit + 1):
            c_share_col = _find_col(df, [f"COMPOSER {i}", "SHARE"])
            c_ctrl_col = _find_col(df, [f"COMPOSER {i}", "CONTROLLED"])
            c_cap_col = _find_col(df, [f"COMPOSER {i}", "CAPACITY"])
            c_link_pub_col = _find_col(df, [f"COMPOSER {i}", "LINKED", "PUBLISHER"])
            
            p_name_col = _find_col(df, [f"PUBLISHER {i}", "NAME"])
            p_cae_col = _find_col(df, [f"PUBLISHER {i}", "CAE"])
            p_aff_col = _find_col(df, [f"PUBLISHER {i}", "AFFILIATION"])
            p_cap_col_fixed = _find_col(df, [f"PUBLISHER {i}", "CAPACITY"])
            p_share_col = _find_col(df, [f"PUBLISHER {i}", "SHARE"])

            c_share_raw = row.get(c_share_col) if c_share_col else None
            c_share_val = 0.0
            
            if _is_empty(c_share_raw):
                 add_err(f"Composer {i} Share is missing or not matched")
            else:
                c_share_val = _parse_float(c_share_raw)
            
            total_share += c_share_val

            c_ctrl_val = _norm_str(row.get(c_ctrl_col)).upper() if c_ctrl_col else ""
            if c_ctrl_val not in ["Y", "N"]:
                add_err(f"Composer {i} Controlled is missing or not matched")

            c_cap_val = _norm_str(row.get(c_cap_col)).upper() if c_cap_col else ""
            if c_cap_val not in ["A", "C", "AC", "CA"]:
                add_err(f"Composer {i} Capacity is missing or not matched")

            link_pub_val = _norm_str(row.get(c_link_pub_col)) if c_link_pub_col else ""
            if link_pub_val == "":
                add_err(f"Composer {i} Linked Publisher is missing or not matched")
            
            is_elite = link_pub_val.upper() == "ELITE EMBASSY PUBLISHING"
            is_music_emb = link_pub_val.upper() == "MUSIC EMBASSIES PUBLISHING"

            if is_elite:
                if _norm_str(row.get(p_name_col)).upper() != "ELITE EMBASSY PUBLISHING":
                    add_err(f"Publisher {i} Name is missing or not matched")
                p_cae_val = _norm_str(row.get(p_cae_col)).replace(".0", "")
                if p_cae_val != "619851030":
                     add_err(f"Publisher {i} CAE No is missing or not matched")
                if _norm_str(row.get(p_aff_col)).upper() != "BMI":
                    add_err(f"Publisher {i} Affiliation is missing or not matched")
            
            elif is_music_emb:
                if _norm_str(row.get(p_name_col)).upper() != "MUSIC EMBASSIES PUBLISHING":
                    add_err(f"Publisher {i} Name is missing or not matched")
                p_cae_val = _norm_str(row.get(p_cae_col)).replace(".0", "")
                if p_cae_val != "741593140":
                     add_err(f"Publisher {i} CAE No is missing or not matched")
                if _norm_str(row.get(p_aff_col)).upper() != "ASCAP":
                    add_err(f"Publisher {i} Affiliation is missing or not matched")

            p_cap_val = _norm_str(row.get(p_cap_col_fixed)).upper() if p_cap_col_fixed else ""
            if p_cap_val != "OP":
                add_err(f"Publisher {i} Capacity is missing or not matched (Should be OP)")

            p_share_raw = row.get(p_share_col) if p_share_col else 0
            if _is_empty(p_share_raw):
                add_err(f"Publisher {i} Share is missing or not matched")
            else:
                p_share_val = _parse_float(p_share_raw)
                if abs(p_share_val - c_share_val) > 0.01:
                    add_err(f"Publisher {i} Share does not match Composer {i} Share")

        if w_count > 0:
            if abs(total_share - 100.0) > 0.1:
                 add_err(f"Total Share is not 100% (Found {total_share}%)")

    return errors