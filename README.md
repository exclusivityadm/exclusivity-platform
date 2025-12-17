# Exclusivity v1 – Final Rebuild 

- FastAPI backend (modular routers)
- Next.js 14 app-dir frontend (TS)
- Hardhat contracts for LUXToken
- Vercel + Render friendly
- Base + Alchemy ready

## Backend
pip install -r requirements.txt
uvicorn apps.backend.main:app --reload

## Frontend
cd apps/frontend
npm install
npm run dev

## Contracts
cd contracts/hardhat
cp .env.example .env
# fill ALCHEMY_HTTP_URL + PRIVATE_KEY (without 0x)
npm install
npx hardhat compile
npx hardhat run scripts/deploy.ts --network base
