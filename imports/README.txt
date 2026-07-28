CATHOLIC PORTAL — IMPORTAZIONE RAPIDA

Inserire i quattro file originali nella cartella dell’esame.

ESEMPIO HSPT EXAM 1:

imports/hspt/hspt_full_exam_01_part_a.docx
imports/hspt/hspt_full_exam_01_part_b.docx
imports/hspt/hspt_full_exam_01_part_c.docx
imports/hspt/hspt_full_exam_01_part_d.docx

Sono accettati sia DOCX sia TXT.

IMPORTARE SOLO HSPT EXAM 1:

python3 tools/import_catholic_exams.py --family hspt --exam 1

CONTROLLARE SENZA CREARE JSON:

python3 tools/import_catholic_exams.py --family hspt --exam 1 --dry-run

IMPORTARE TUTTO QUELLO CHE È PRESENTE:

python3 tools/import_catholic_exams.py --family all

VALIDARE TUTTI I JSON GIÀ CREATI:

python3 tools/import_catholic_exams.py --validate-json

REPORT:

imports/reports/

CORREZIONI MANUALI MIRATE:

imports/item_overrides.json
