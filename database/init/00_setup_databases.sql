-- ============================================================
-- Script: Download and restore WideWorldImporters database
-- ============================================================
-- Este script descarga WideWorldImporters desde Microsoft
-- y la restaura en SQL Server dentro de Docker
--
-- Nota: Ejecutar en el contenedor de SQL Server
-- ============================================================

USE [master];

-- 1. Crear directorio para backup (dentro del contenedor)
-- En el contenedor: /var/opt/mssql/backup/

-- 2. Descargar el archivo .bak desde Microsoft
-- Comando en terminal:
-- docker exec wwidw_mssql bash -c "cd /var/opt/mssql/backup && curl -L -o WideWorldImporters-Full.bak 'https://github.com/Microsoft/sql-server-samples/releases/download/wide-world-importers-v1.0/WideWorldImporters-Full.bak'"

-- 3. Restaurar la base de datos
RESTORE DATABASE [WideWorldImporters]
FROM DISK = '/var/opt/mssql/backup/WideWorldImporters-Full.bak'
WITH MOVE 'WWI_Primary' TO '/var/opt/mssql/data/WideWorldImporters.mdf',
     MOVE 'WWI_UserData' TO '/var/opt/mssql/data/WideWorldImporters_UserData.ndf',
     MOVE 'WWI_Log' TO '/var/opt/mssql/data/WideWorldImporters.ldf',
     REPLACE,
     RECOVERY;

-- 4. Verificar que la base fue restaurada
SELECT name, state_desc FROM sys.databases WHERE name = 'WideWorldImporters';

-- 5. Crear esquemas para Staging y Data Warehouse
CREATE DATABASE [WideWorldImporters_Staging];
GO
CREATE DATABASE [WideWorldImporters_DW];
GO

PRINT 'Bases de datos creadas exitosamente:';
SELECT name FROM sys.databases WHERE name IN ('WideWorldImporters', 'WideWorldImporters_Staging', 'WideWorldImporters_DW');
