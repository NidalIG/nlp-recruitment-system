import express from 'express';
import cors from 'cors';
import multer from 'multer';
import pdf from 'pdf-parse';
import PDFDocument from 'pdfkit';

const app = express();
const PORT = process.env.PORT || 3001;
const GEMINI_API_KEY = process.env.GEMINI_API_KEY || '';

app.use(cors());
app.use(express.json({ limit: '12mb' })); // JSON body (quiz/chat/match); Upload handled by multer

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 20 * 1024 * 1024 }, // 20MB
  fileFilter: (req, file, cb) => {
    const ok = ['application/pdf', 'text/plain'];
    if (ok.includes(file.mimetype) || file.originalname.toLowerCase().endsWith('.pdf') || file.originalname.toLowerCase().endsWith('.txt')) return cb(null, true);
    cb(new Error('Type de fichier non supporté. Utilisez PDF ou TXT.'));
  },
});

function hasPDFHeader(buf){ try{ return buf?.slice(0,4).toString()==='%PDF'; }catch{ return false; } }

// ---------- Upload & Parsing ----------
app.post('/api/upload', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) return res.status(400).json({ error: 'Aucun fichier' });
    const isPdf = req.file.mimetype.includes('pdf') || req.file.originalname.toLowerCase().endsWith('.pdf');
    let text = '';
    let warning = '';

    if (isPdf) {
      if (!hasPDFHeader(req.file.buffer)) {
        warning = 'Le fichier ne semble pas être un PDF texte valide (signature %PDF manquante). Réexportez en PDF/A.';
      } else {
        try {
          const data = await pdf(req.file.buffer);
          text = (data.text || '').trim();
          if (!text) warning = 'PDF probablement scanné (image) / protégé — aucun texte détecté. Utilisez un PDF texte ou passez par un OCR.';
        } catch (e) {
          warning = 'Lecture du PDF impossible (corrompu/chiffré). Réexportez en PDF texte et réessayez.';
        }
      }
    } else {
      text = req.file.buffer.toString('utf-8');
    }

    return res.status(200).json({ filename: req.file.originalname, text, warning, warning_human: warning });
  } catch (e) {
    console.error('UPLOAD ERROR', e);
    return res.status(200).json({ filename: req.file?.originalname || '', text: '', warning: 'Erreur parsing — réessayez avec un PDF/TXT texte.' });
  }
});

// ---------- Matching ----------
const STOP = new Set(['a','à','au','aux','le','la','les','de','des','du','un','une','et','ou','en','pour','par','avec','sur','dans','que','qui','quoi','dont','comme','ce','cet','cette','ces','est','sont','être','avoir','faire','plus','moins','très','tres','the','of','to','and','in','on','for','with','as','is','are','be','have','do']);
function normalize(text=''){return text.toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu,'').replace(/[^a-z0-9\s]/g,' ').replace(/\s+/g,' ').trim();}
function tokens(text=''){return new Set(normalize(text).split(' ').filter(t=>t && !STOP.has(t)));}
function jaccard(aText,bText){const A=tokens(aText),B=tokens(bText); if(A.size===0&&B.size===0)return 0; const inter=[...A].filter(x=>B.has(x)).length; const uni=new Set([...A,...B]).size; return (inter/uni)*100;}
function missingKeywords(cvText,jobText){const A=tokens(cvText),B=tokens(jobText);return [...B].filter(x=>!A.has(x)).slice(0,25);}
function suggestImprovements(jobText){const t=normalize(jobText);const s=[];const needs=(...k)=>k.some(x=>t.includes(x));if(needs('react','next'))s.push('Projet React/Next.js (CRUD + auth + tests)');if(needs('node','express'))s.push('API REST Node/Express avec tests et Swagger');if(needs('python'))s.push('Certif Python (PCAP) + script ETL');if(needs('sql','postgres','mysql'))s.push('Base Postgres + requêtes SQL avancées');if(needs('aws','azure','gcp'))s.push('Certif Cloud Practitioner');if(needs('docker','kubernetes'))s.push('Dockeriser une app + déploiement K8s');if(needs('nlp','spacy','transformer','huggingface'))s.push('Projet NLP (extraction compétences + matching)');if(s.length===0)s.push('Ajouter des projets concrets liés aux mots‑clés de l’offre.');return s.slice(0,6);}

app.post('/api/match', async (req, res) => {
  try {
    const { cvText = '', jobText = '' } = req.body || {};
    if (!cvText.trim() || !jobText.trim()) return res.status(400).json({ error: 'Textes requis' });
    const score = jaccard(cvText, jobText);
    const missing = missingKeywords(cvText, jobText);
    const suggestions = score < 60 ? suggestImprovements(jobText) : [];
    return res.json({ score, missingKeywords: missing, suggestions });
  } catch (e) {
    console.error(e);
    return res.status(500).json({ error: 'Erreur calcul matching' });
  }
});

// ---------- Chat (stub) ----------
app.post('/api/chat', async (req, res) => {
  try {
    const { messages = [] } = req.body || {};
    const last = messages[messages.length - 1]?.content || '';
    const hint = last.slice(0, 120);
    return res.json({ message: { role: 'assistant', content: `Réponse de démo — branchez votre modèle IA.\nDernier message: \"${hint}\"` } });
  } catch (e) { return res.status(500).json({ error: 'Erreur chat' }); }
});

// ---------- PDF Report ----------
app.post('/api/report', async (req, res) => {
  try {
    const { cvText = '', jobText = '', score = 0, missingKeywords = [], suggestions = [] } = req.body || {};
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', 'attachment; filename=\"rapport-matching.pdf\"');
    const doc = new PDFDocument({ size: 'A4', margin: 50 });
    doc.pipe(res);
    doc.fontSize(18).text('Rapport de Matching CV ↔ Offre', { align: 'center' }); doc.moveDown();
    doc.fontSize(12).text(`Score global: ${Math.round(score)}%`); doc.moveDown(0.5);
    if (missingKeywords.length){ doc.fontSize(12).text('Mots-clés manquants:'); doc.fontSize(10).list(missingKeywords); doc.moveDown(); }
    if (suggestions.length){ doc.fontSize(12).text('Suggestions:'); doc.fontSize(10).list(suggestions); doc.moveDown(); }
    doc.moveDown().fontSize(12).text('Job Description (extrait):', { underline: true }); doc.fontSize(10).text(jobText.slice(0, 2000) || '-', { align: 'left' }); doc.moveDown();
    doc.fontSize(12).text('CV (extrait):', { underline: true }); doc.fontSize(10).text(cvText.slice(0, 2000) || '-', { align: 'left' });
    doc.end();
  } catch (e) { console.error(e); return res.status(500).json({ error: 'Erreur génération PDF' }); }
});

// ---------- Quiz (Gemini) ----------
function buildQuizPrompt(level='facile', count=5, topic='Général'){
  return `Tu es un générateur de quiz. Crée ${count} questions à choix multiple en français sur le thème: ${topic}.
Niveau: ${level}.
Retourne STRICTEMENT un JSON valide de la forme:
{"questions":[{"id":"q1","question":"...","choices":["A","B","C","D"],"answerIndex":0,"explanation":"..."}]}
- 3 à 4 propositions par question.
- answerIndex doit pointer sur l'index de 'choices'.
- Pas de texte avant/après le JSON.`;
}

function extractJSON(text=''){
  try {
    const start = text.indexOf('{');
    const end = text.lastIndexOf('}');
    if (start>=0 && end>start) {
      const slice = text.slice(start, end+1);
      return JSON.parse(slice);
    }
  } catch {}
  return null;
}

app.post('/api/quiz', async (req, res) => {
  try {
    const { level = 'facile', count = 5, topic = 'Général' } = req.body || {};
    if (!GEMINI_API_KEY) {
      // Fallback local demo so l'UI marche sans clé
      const demo = Array.from({length: Math.min(10, Number(count)||5)}, (_,i)=> ({
        id: 'q'+(i+1),
        question: `Question démo ${i+1} sur ${topic}?`,
        choices: ['Option A','Option B','Option C','Option D'],
        answerIndex: i%4,
        explanation: "Ceci est un exemple local (ajoutez GEMINI_API_KEY pour de vraies questions)."
      }));
      return res.json({ provider: 'demo', questions: demo });
    }

    const prompt = buildQuizPrompt(level, count, topic);
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${encodeURIComponent(GEMINI_API_KEY)}`;
    const payload = { contents: [{ role: 'user', parts: [{ text: prompt }] }] };
    const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const out = await r.json();

    const text = out?.candidates?.[0]?.content?.parts?.[0]?.text || '';
    const parsed = extractJSON(text);
    if (!parsed?.questions?.length) {
      return res.status(502).json({ error: 'Réponse du modèle illisible', raw: text });
    }
    return res.json({ provider: 'gemini', questions: parsed.questions });
  } catch (e) {
    console.error('QUIZ ERROR', e);
    return res.status(500).json({ error: 'Erreur génération quiz' });
  }
});

// ---------- Error handler (always JSON) ----------
app.use((err, req, res, next) => {
  if (err) {
    const code = err.status || 400;
    return res.status(code).json({ error: err.message || 'Erreur' });
  }
  next();
});

app.listen(PORT, () => console.log(`Server listening on http://localhost:${PORT}`));
