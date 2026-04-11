import os
from supabase import create_client, Client

class SupabaseStorage:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        self.bucket_name = os.getenv("SUPABASE_BUCKET_NAME", "ragforge-docs")
        
        self.supabase: Client = create_client(url, key)

    def upload_file(self, file_path: str, remote_path: str):
        """Uploads a local file to Supabase storage."""
        with open(file_path, 'rb') as f:
            self.supabase.storage.from_(self.bucket_name).upload(
                path=remote_path,
                file=f,
                file_options={"upsert": "true"}
            )
        return remote_path

    def upload_bytes(self, data: bytes, remote_path: str):
        """Uploads raw bytes (like a JSON string or PDF) directly."""
        self.supabase.storage.from_(self.bucket_name).upload(
            path=remote_path,
            file=data,
            file_options={"upsert": "true"}
        )
        return remote_path

    def download_file(self, remote_path: str):
        """Downloads a file from Supabase and returns the bytes."""
        return self.supabase.storage.from_(self.bucket_name).download(remote_path)

    def list_files(self, folder: str = ""):
        """Lists files in a specific Supabase folder."""
        return self.supabase.storage.from_(self.bucket_name).list(path=folder)

    def get_public_url(self, remote_path: str):
        """Gets a public URL (works since you set your bucket to Public)."""
        return self.supabase.storage.from_(self.bucket_name).get_public_url(remote_path)
