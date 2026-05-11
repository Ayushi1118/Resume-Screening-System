from flask import Flask, request, jsonify, send_file
from flask_cors import CORS 
import re

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return send_file("index.html")
#text extraction

def extract_text_from_pdf(file_bytes):
    try:
        import pypdf
        import io
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        return " ".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        return ""

def extract_text_from_docx(file_bytes):
    try:
        import docx
        import io
        doc = docx.Document(io.BytesIO(file_bytes))
        return " ".join(p.text for p in doc.paragraphs)
    except Exception as e:
        return ""

def extract_text(file_bytes, filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext in ("docx", "doc"):
        return extract_text_from_docx(file_bytes)
    return ""


STOP_WORDS = {
    "a","an","the","and","or","but","in","on","at","to","for","of","with",
    "by","from","is","are","was","were","be","been","being","have","has",
    "had","do","does","did","will","would","could","should","may","might",
    "shall","can","need","dare","ought","used","i","we","you","he","she",
    "it","they","their","our","your","its","this","that","these","those",
    "as","if","so","yet","both","either","neither","not","no","nor","only",
    "own","same","than","too","very","just","because","while","although",
    "however","therefore","thus","hence","also","well","up","out","about",
    "into","through","during","before","after","above","below","between",
    "each","few","more","most","other","some","such","any","all","both"
}

def tokenize(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s\+\#]', ' ', text)
    tokens = text.split()
    return [t for t in tokens if len(t) > 2 and t not in STOP_WORDS]

def compute_match(jd_text, resume_text):
    jd_tokens = tokenize(jd_text)
    resume_tokens = tokenize(resume_text)
    
    jd_set = set(jd_tokens)
    resume_set = set(resume_tokens)
    
    matched = sorted(jd_set & resume_set)
    missing = sorted(jd_set - resume_set)
    
    score = (len(matched) / len(jd_set) * 100) if jd_set else 0
    
    return round(score, 1), matched[:15], missing[:15]



@app.route("/screen", methods=["POST"])
def screen():
    job_description = request.form.get("job_description", "").strip()
    files = request.files.getlist("resumes")

    if not job_description:
        return jsonify({"error": "Job description is required."}), 400
    if not files:
        return jsonify({"error": "Please upload at least one resume."}), 400

    results = []
    for f in files:
        raw   = f.read()
        text  = extract_text(raw, f.filename)
        score, matched, missing = compute_match(job_description, text)
        results.append({
            "filename": f.filename,
            "score":    score,
            "matched":  matched,
            "missing":  missing,
            "preview":  text[:300].strip() if text else "Could not extract text."
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return jsonify({"results": results})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
