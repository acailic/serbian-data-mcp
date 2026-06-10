# API Konekcija - Serbian Data MCP Server

## Da li trebaju kredencijali?

**NE!** ❌ Nisu potrebni nikakvi kredencijali.

Server se povezuje na **data.gov.rs** (javni srpski portal otvorenih podataka) koji je **potpuno otvoren i javan**.

---

## Kako funkcioniše?

### 1. Automatska konekcija

Server se automatski povezuje na API bez ikakvih podešavanja:

```python
from serbian_data_mcp.api.client import UDataClient

client = UDataClient()  # ✅ Samo to - ništa više!

# Spremno radi
datasets = await client.search_datasets("population")
```

### 2. Šta se dešava u pozadini?

```python
# UDataClient.__init__ (self.api.client.py:34-54)
def __init__(self, base_url=None, rate_limit=None, timeout=None):
    # Koristi config vrednosti ili podrazumevane
    self.base_url = base_url or config.api_base  # "https://data.gov.rs"
    self.rate_limit = rate_limit or config.rate_limit  # 0.1 sekunde
    self.timeout = timeout or config.timeout  # 30 sekundi
    
    # Kreira HTTP klijent - BEZ AUTHENTICATION
    self._client = httpx.AsyncClient(
        base_url=self.base_url,
        timeout=self.timeout,
        headers={"User-Agent": "SerbianDataMCP/1.0"}  # Samo identifikacija
    )
```

### 3. Bezbednosne mere

Iako nema autentikacije, server ima zaštitu:

- **SSRF zaštita** - Blokira pristup privatnim IP adresama (localhost, 10.0.0.0/8, itd.)
- **Rate limiting** - Čeka 0.1 sekundi između zahteva (poštovanje API ja)
- **Whitelist domena** - Dozvoljeni samo određeni domeni za resurse
- **Retry logic** - Automatski pokušava ponovo (3 puta sa exponential backoff)

---

## Konfiguracija

Ako želiš da promeniš podešavanja, dodaj u `.env` fajl:

```bash
# API konekcija
API_BASE=https://data.gov.rs
RATE_LIMIT=0.1
TIMEOUT=30

# Cache (lokalno čuvanje)
CACHE_DIR=.cache
DEFAULT_CACHE_TTL=300
```

Ali **nisi moraš** - sve radi sa podrazumevanim vrednostima!

---

## Testiranje konekcije

```bash
# Testiraj konekciju
python test_connection.sh

# Ili ručno
uv run python -c "
import asyncio
from serbian_data_mcp.api.client import UDataClient

async def test():
    client = UDataClient()
    result = await client.search_datasets('population', page_size=5)
    print(f'✅ Konekcija uspešna! Pronađeno {result.total} datasetova')

asyncio.run(test())
"
```

---

## Zaključak

✅ **Nema potrebe za kredencijale**  
✅ **Automatska konekcija** - samo importuj i koristi  
✅ **Javni portal** - data.gov.rs je otvoren za sve  
✅ **Bezbedno** - SSRF zaštita, rate limiting, whitelist

**Samo koristi:** `client = UDataClient()` i sve radi! 🎉
