git clone https://github.com/Priyangshu139/PhotonTroppers.git

python -m venv venv

powershell-
.\venv\Scripts\Activate.ps1 
bash-
source venv/Scripts/activate

pip install -r requirements.txt

uvicorn app.main:app --reload  

http://127.0.0.1:8000/docs
