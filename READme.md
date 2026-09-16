#1 Backend terminali

Projenin root klasöründe ol:
cd C:\Users\Buket\OneDrive\Desktop\sdg-project-advanced

Virtual environment’i aktive et:

.\.venv\Scripts\Activate.ps1

Sonra backend’i başlat:

uvicorn backend.app:app --reload

Doğru açılırsa şuna benzer bir şey görürsün:

Uvicorn running on http://127.0.0.1:8000

İstersen kontrol için browser’da aç:

http://localhost:8000/docs

Burada GET /api/courses ve POST /api/evaluate görünmeli.

2) Frontend terminali

Yeni bir PowerShell aç:

cd C:\Users\Buket\OneDrive\Desktop\sdg-project-advanced\frontend

Sonra:

npm run dev

Vite sana genelde şunu verir:

http://localhost:5173

Onu browser’da aç.

Akış:

Terminal 1:
uvicorn backend.app:app --reload

Terminal 2:
cd frontend
npm run dev

Sonra frontend’de course seçip Evaluate Course butonuna basıyorsun.

Durdurmak istersen ilgili terminalde:

Ctrl + C

basman yeterli.