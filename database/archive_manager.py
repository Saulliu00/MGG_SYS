"""
Parquet Archive Manager
Handles archiving of old data from PostgreSQL to Parquet files
"""

import os
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime, timedelta
from sqlalchemy import text
import logging
import hashlib
from pathlib import Path

from db_config import get_db_session, DatabaseConfig

logger = logging.getLogger(__name__)


class ArchiveManager:
    """Manage data archival from PostgreSQL to Parquet files"""

    def __init__(self, archive_path=None, compression='snappy'):
        """
        Initialize Archive Manager

        Args:
            archive_path: Path to store Parquet files
            compression: Compression algorithm (snappy, gzip, brotli, zstd)
        """
        self.archive_path = archive_path or DatabaseConfig.ARCHIVE_PATH
        self.compression = compression or DatabaseConfig.COMPRESSION

        # Create archive directories
        os.makedirs(self.archive_path, exist_ok=True)

    def archive_table(self, table_name, start_date, end_date, user_id=None):
        """
        Archive data from a table to Parquet file

        Args:
            table_name: Name of the table to archive
            start_date: Start date for archival
            end_date: End date for archival
            user_id: User performing the archive

        Returns:
            dict with archive information
        """
        try:
            logger.info(f"Starting archive for {table_name} from {start_date} to {end_date}")

            # Generate batch name
            batch_name = f"{table_name}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"

            # Query data from PostgreSQL
            with get_db_session() as session:
                # Get data based on table
                if table_name == 'simulation_time_series':
                    query = text("""
                        SELECT sts.*, fs.work_order_id, fs.user_id, fs.nc_amount, fs.created_at as simulation_date
                        FROM simulation_time_series sts
                        JOIN forward_simulations fs ON sts.simulation_id = fs.id
                        WHERE fs.created_at >= :start_date AND fs.created_at < :end_date
                        ORDER BY sts.simulation_id, sts.sequence_number
                    """)
                elif table_name == 'test_time_series':
                    query = text("""
                        SELECT tts.*, tr.work_order_id, tr.user_id, tr.test_date
                        FROM test_time_series tts
                        JOIN test_results tr ON tts.test_result_id = tr.id
                        WHERE tr.test_date >= :start_date AND tr.test_date < :end_date
                        ORDER BY tts.test_result_id, tts.sequence_number
                    """)
                elif table_name == 'operation_logs':
                    query = text("""
                        SELECT *
                        FROM operation_logs
                        WHERE created_at >= :start_date AND created_at < :end_date
                        ORDER BY created_at
                    """)
                else:
                    raise ValueError(f"Unsupported table for archival: {table_name}")

                # Execute query and load into DataFrame
                df = pd.read_sql(query, session.bind, params={
                    'start_date': start_date,
                    'end_date': end_date
                })

            if df.empty:
                logger.warning(f"No data found for {table_name} in date range")
                return {'success': False, 'message': 'No data to archive'}

            # Create table-specific directory
            table_path = os.path.join(self.archive_path, table_name)
            os.makedirs(table_path, exist_ok=True)

            # Create Parquet file
            parquet_file = os.path.join(table_path, f"{batch_name}.parquet")

            # Convert to Parquet with compression
            table = pa.Table.from_pandas(df)
            pq.write_table(
                table,
                parquet_file,
                compression=self.compression,
                use_dictionary=True,
                write_statistics=True
            )

            # Calculate file size and checksum
            file_size = os.path.getsize(parquet_file)
            checksum = self._calculate_checksum(parquet_file)

            logger.info(f"Created Parquet file: {parquet_file} ({file_size} bytes)")

            # Record archive in database
            with get_db_session() as session:
                archive_record = text("""
                    INSERT INTO archive_batches
                    (batch_name, table_name, start_date, end_date, row_count,
                     parquet_file_path, parquet_file_size, compression_type,
                     archived_by, status, checksum)
                    VALUES
                    (:batch_name, :table_name, :start_date, :end_date, :row_count,
                     :parquet_file_path, :parquet_file_size, :compression_type,
                     :archived_by, 'completed', :checksum)
                    RETURNING id
                """)

                result = session.execute(archive_record, {
                    'batch_name': batch_name,
                    'table_name': table_name,
                    'start_date': start_date,
                    'end_date': end_date,
                    'row_count': len(df),
                    'parquet_file_path': parquet_file,
                    'parquet_file_size': file_size,
                    'compression_type': self.compression,
                    'archived_by': user_id,
                    'checksum': checksum
                })

                archive_id = result.fetchone()[0]

            logger.info(f"Archive completed: {len(df)} rows archived")

            return {
                'success': True,
                'archive_id': archive_id,
                'batch_name': batch_name,
                'row_count': len(df),
                'file_size': file_size,
                'parquet_file': parquet_file
            }

        except Exception as e:
            logger.error(f"Archive failed: {str(e)}")
            raise

    def delete_archived_data(self, table_name, start_date, end_date):
        """
        Delete data that has been successfully archived

        Args:
            table_name: Name of the table
            start_date: Start date
            end_date: End date

        Returns:
            Number of rows deleted
        """
        try:
            with get_db_session() as session:
                if table_name == 'simulation_time_series':
                    delete_query = text("""
                        DELETE FROM simulation_time_series
                        WHERE simulation_id IN (
                            SELECT id FROM forward_simulations
                            WHERE created_at >= :start_date AND created_at < :end_date
                        )
                    """)
                elif table_name == 'test_time_series':
                    delete_query = text("""
                        DELETE FROM test_time_series
                        WHERE test_result_id IN (
                            SELECT id FROM test_results
                            WHERE test_date >= :start_date AND test_date < :end_date
                        )
                    """)
                elif table_name == 'operation_logs':
                    delete_query = text("""
                        DELETE FROM operation_logs
                        WHERE created_at >= :start_date AND created_at < :end_date
                    """)
                else:
                    raise ValueError(f"Unsupported table: {table_name}")

                result = session.execute(delete_query, {
                    'start_date': start_date,
                    'end_date': end_date
                })

                deleted_count = result.rowcount

            logger.info(f"Deleted {deleted_count} rows from {table_name}")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete archived data: {str(e)}")
            raise

    def restore_from_archive(self, batch_name):
        """
        Restore data from Parquet archive back to PostgreSQL

        Args:
            batch_name: Name of the archive batch

        Returns:
            Number of rows restored
        """
        try:
            # Get archive info from database
            with get_db_session() as session:
                query = text("""
                    SELECT table_name, parquet_file_path, checksum
                    FROM archive_batches
                    WHERE batch_name = :batch_name
                """)

                result = session.execute(query, {'batch_name': batch_name}).fetchone()

                if not result:
                    raise ValueError(f"Archive batch not found: {batch_name}")

                table_name, parquet_file, expected_checksum = result

            # Verify file exists and checksum
            if not os.path.exists(parquet_file):
                raise FileNotFoundError(f"Parquet file not found: {parquet_file}")

            actual_checksum = self._calculate_checksum(parquet_file)
            if actual_checksum != expected_checksum:
                raise ValueError("Checksum mismatch! File may be corrupted.")

            # Read Parquet file
            df = pd.read_parquet(parquet_file)

            # Insert back into PostgreSQL
            with get_db_session() as session:
                df.to_sql(
                    table_name,
                    session.bind,
                    if_exists='append',
                    index=False,
                    method='multi',
                    chunksize=1000
                )

            logger.info(f"Restored {len(df)} rows from {batch_name}")
            return len(df)

        except Exception as e:
            logger.error(f"Failed to restore from archive: {str(e)}")
            raise

    def run_retention_policy(self, table_name=None):
        """
        Run retention policy to archive old data

        Args:
            table_name: Specific table (None = all tables)
        """
        try:
            with get_db_session() as session:
                # Get retention policies
                if table_name:
                    query = text("""
                        SELECT table_name, retention_days, archive_enabled, delete_after_archive
                        FROM retention_policies
                        WHERE table_name = :table_name
                    """)
                    policies = session.execute(query, {'table_name': table_name}).fetchall()
                else:
                    query = text("""
                        SELECT table_name, retention_days, archive_enabled, delete_after_archive
                        FROM retention_policies
                        WHERE archive_enabled = true
                    """)
                    policies = session.execute(query).fetchall()

            # Process each policy
            for policy in policies:
                table_name, retention_days, archive_enabled, delete_after_archive = policy

                if not archive_enabled:
                    continue

                # Calculate date range
                cutoff_date = datetime.now() - timedelta(days=retention_days)
                start_date = cutoff_date - timedelta(days=90)  # Archive 90 days at a time

                logger.info(f"Processing retention for {table_name}: archiving data before {cutoff_date}")

                # Archive data
                result = self.archive_table(table_name, start_date, cutoff_date)

                if result['success'] and delete_after_archive:
                    # Delete archived data
                    self.delete_archived_data(table_name, start_date, cutoff_date)

                # Update last cleanup time
                with get_db_session() as session:
                    update_query = text("""
                        UPDATE retention_policies
                        SET last_cleanup_at = CURRENT_TIMESTAMP
                        WHERE table_name = :table_name
                    """)
                    session.execute(update_query, {'table_name': table_name})
    
        except Exception as e:
            logger.error(f"Retention policy execution failed: {str(e)}")
            raise

    def _calculate_checksum(self, file_path):
        """Calculate SHA256 checksum of a file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def list_archives(self, table_name=None):
        """
        List all archive batches

        Args:
            table_name: Filter by table name (optional)

        Returns:
            List of archive batches
        """
        with get_db_session() as session:
            if table_name:
                query = text("""
                    SELECT * FROM archive_batches
                    WHERE table_name = :table_name
                    ORDER BY archived_at DESC
                """)
                results = session.execute(query, {'table_name': table_name}).fetchall()
            else:
                query = text("""
                    SELECT * FROM archive_batches
                    ORDER BY archived_at DESC
                """)
                results = session.execute(query).fetchall()

        return results

    def get_archive_stats(self):
        """Get statistics about archived data"""
        with get_db_session() as session:
            query = text("""
                SELECT
                    table_name,
                    COUNT(*) as batch_count,
                    SUM(row_count) as total_rows,
                    SUM(parquet_file_size) as total_size,
                    MIN(start_date) as earliest_date,
                    MAX(end_date) as latest_date
                FROM archive_batches
                WHERE status = 'completed'
                GROUP BY table_name
                ORDER BY table_name
            """)

            results = session.execute(query).fetchall()

        return results


if __name__ == "__main__":
    # Example usage
    archive_mgr = ArchiveManager()

    # Run retention policies
    print("Running retention policies...")
    archive_mgr.run_retention_policy()

    # Show archive stats
    print("\nArchive Statistics:")
    stats = archive_mgr.get_archive_stats()
    for stat in stats:
        print(f"  {stat[0]}: {stat[1]} batches, {stat[2]} rows, {stat[3]} bytes")
