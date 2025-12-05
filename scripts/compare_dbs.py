import sqlite3
import os

os.chdir("proj2")

def get_counts(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    tables = ['User', 'Restaurant', 'MenuItem', '"Order"', 'OrderItems', 'Review', 'Analytics']
    counts = {}
    for table in tables:
        try:
            c.execute(f'SELECT COUNT(*) FROM {table}')
            counts[table] = c.fetchone()[0]
        except Exception as e:
            counts[table] = f'ERROR: {e}'
    conn.close()
    return counts

print('Current DB (CSC510_DB.db):')
current = get_counts('CSC510_DB.db')
for table, count in current.items():
    print(f'  {table}: {count}')

print('\nBackup DB (CSC510_DB.db.backup.20251119_183208):')
backup = get_counts('CSC510_DB.db.backup.20251119_183208')
for table, count in backup.items():
    print(f'  {table}: {count}')

print('\nDifferences:')
all_same = True
for table in current:
    if current[table] != backup[table]:
        print(f'  {table}: current={current[table]}, backup={backup[table]}')
        all_same = False
    else:
        print(f'  {table}: SAME ({current[table]})')

if all_same:
    print('\n✓ Databases are identical!')
else:
    print('\n✗ Databases have differences')
