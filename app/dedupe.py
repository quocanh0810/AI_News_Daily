from sqlalchemy import select, delete
from rapidfuzz import fuzz
from .db import SessionLocal
from .models import News

def dedupe_titles(threshold=90):
    with SessionLocal() as s:
        items = s.execute(select(News)).scalars().all()
        to_delete = set()
        for i in range(len(items)):
            if items[i].id in to_delete: 
                continue
            for j in range(i+1, len(items)):
                if items[j].id in to_delete:
                    continue
                score = fuzz.token_set_ratio(items[i].title, items[j].title)
                if score >= threshold:
                    # keep earlier published (lower id)
                    keep = items[i] if items[i].id < items[j].id else items[j]
                    drop = items[j] if keep is items[i] else items[i]
                    to_delete.add(drop.id)
        if to_delete:
            s.execute(delete(News).where(News.id.in_(list(to_delete))))
            s.commit()
        return len(to_delete)

if __name__ == "__main__":
    n = dedupe_titles()
    print(f"Removed {n} duplicates")
