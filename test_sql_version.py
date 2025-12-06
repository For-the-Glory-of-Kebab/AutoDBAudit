"""Quick test of SQL version detection."""
import pyodbc

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=localhost\\INTHEEND;'
    'UID=sa;'
    'PWD=K@vand24;'
    'TrustServerCertificate=yes'
)
cursor = conn.cursor()
cursor.execute("""
    SELECT 
        CAST(SERVERPROPERTY('ServerName') AS NVARCHAR(256)) AS ServerName,
        CAST(SERVERPROPERTY('InstanceName') AS NVARCHAR(256)) AS InstanceName,
        CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128)) AS Version,
        CAST(PARSENAME(CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128)), 4) AS INT) AS VersionMajor,
        CAST(SERVERPROPERTY('Edition') AS NVARCHAR(256)) AS Edition,
        CAST(SERVERPROPERTY('ProductLevel') AS NVARCHAR(128)) AS ProductLevel,
        CAST(SERVERPROPERTY('IsClustered') AS INT) AS IsClustered
""")
row = cursor.fetchone()
print(f'ServerName: {row.ServerName}')
print(f'InstanceName: {row.InstanceName}')
print(f'Version: {row.Version}')
print(f'VersionMajor: {row.VersionMajor}')
print(f'Edition: {row.Edition}')
print(f'ProductLevel: {row.ProductLevel}')
print(f'IsClustered: {row.IsClustered}')
conn.close()
print('\n✅ Version detection works!')
