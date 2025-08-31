# pip install pinecone pypdf sentence-transformers langchain langchain_text_splitters tqdm
"""
PDF to Pinecone Vector Database Script - VSCode Compatible
=========================================================
This script processes PDF files from a local directory and uploads them to Pinecone vector database.
"""

import os
import uuid
import glob
from pathlib import Path
from pinecone import Pinecone
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from tqdm.auto import tqdm

def install_dependencies():
    """
    Install required dependencies. Run this function first if libraries are not installed.
    You can also install them manually using:
    pip install pinecone pypdf sentence-transformers langchain langchain_text_splitters tqdm
    """
    import subprocess
    import sys
    
    packages = [
        "pinecone",
        "pypdf", 
        "sentence-transformers",
        "langchain",
        "langchain_text_splitters",
        "tqdm"
    ]
    
    for package in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--upgrade"])
            print(f"✓ Installed/updated {package}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install {package}: {e}")
            
    print("Dependencies installation completed.")

class PDFToPinecone:
    def __init__(self):
        # Configuration
        self.PINECONE_API_KEY = "pcsk_6jWP9***********************************D1g9dhdq8GtCjz6M"
        self.PINECONE_INDEX_NAME = "scai-index"
        self.EMBEDDING_MODEL_NAME = 'intfloat/multilingual-e5-large'
        self.EXPECTED_DIMENSION = 1024
        self.CHUNK_SIZE = 1000
        self.CHUNK_OVERLAP = 100
        self.PINECONE_BATCH_SIZE = 100
        self.PDF_DIRECTORY = "./pdfs"  # Directory containing PDF files
        
        # Initialize components
        self.pc = None
        self.index = None
        self.embedding_model = None
        self.text_splitter = None
        
    def print_config(self):
        """Print current configuration"""
        print(f"Configuration:")
        print(f" - Pinecone Index: {self.PINECONE_INDEX_NAME}")
        print(f" - Embedding Model: {self.EMBEDDING_MODEL_NAME}")
        print(f" - Expected Dimension: {self.EXPECTED_DIMENSION}")
        print(f" - Chunk Size: {self.CHUNK_SIZE}")
        print(f" - Chunk Overlap: {self.CHUNK_OVERLAP}")
        print(f" - Pinecone Batch Size: {self.PINECONE_BATCH_SIZE}")
        print(f" - PDF Directory: {self.PDF_DIRECTORY}")
        
    def setup_pdf_directory(self):
        """Create PDF directory if it doesn't exist"""
        os.makedirs(self.PDF_DIRECTORY, exist_ok=True)
        print(f"PDF directory ready: {self.PDF_DIRECTORY}")
        
    def get_pdf_files(self):
        """Get list of PDF files from the directory"""
        pdf_pattern = os.path.join(self.PDF_DIRECTORY, "*.pdf")
        pdf_files = glob.glob(pdf_pattern)
        
        if not pdf_files:
            print(f"No PDF files found in {self.PDF_DIRECTORY}")
            print(f"Please add PDF files to the directory: {os.path.abspath(self.PDF_DIRECTORY)}")
            return []
            
        print(f"Found {len(pdf_files)} PDF file(s):")
        for pdf_file in pdf_files:
            print(f"- {os.path.basename(pdf_file)}")
            
        return pdf_files
    
    def initialize_pinecone(self):
        """Initialize Pinecone connection and validate/create index"""
        print("Initializing Pinecone...")
        
        try:
            # Connect to Pinecone
            self.pc = Pinecone(api_key=self.PINECONE_API_KEY)
            print(f"Connecting to Pinecone index '{self.PINECONE_INDEX_NAME}'...")
            
            # Check if index exists
            index_list_response = self.pc.list_indexes()
            
            # Extract index names
            actual_index_names = []
            if hasattr(index_list_response, 'indexes'):
                index_descriptions = index_list_response.indexes
                actual_index_names = [idx.name for idx in index_descriptions]
            elif isinstance(index_list_response, list):
                try:
                    actual_index_names = [idx['name'] for idx in index_list_response]
                except (TypeError, KeyError):
                    actual_index_names = list(index_list_response)
            else:
                actual_index_names = list(index_list_response)
            
            print(f"Available Pinecone indexes: {actual_index_names}")
            
            # Create index if it doesn't exist
            if self.PINECONE_INDEX_NAME not in actual_index_names:
                print(f"Index '{self.PINECONE_INDEX_NAME}' not found. Creating new index...")
                
                try:
                    # Create the index with appropriate configuration
                    from pinecone import ServerlessSpec
                    
                    self.pc.create_index(
                        name=self.PINECONE_INDEX_NAME,
                        dimension=self.EXPECTED_DIMENSION,
                        metric='cosine',  # or 'euclidean', 'dotproduct'
                        spec=ServerlessSpec(
                            cloud='aws',  # or 'gcp'
                            region='us-east-1'  # adjust based on your preference
                        )
                    )
                    
                    # Wait for index to be ready
                    print("Waiting for index to be ready...")
                    import time
                    while self.PINECONE_INDEX_NAME not in [idx.name for idx in self.pc.list_indexes().indexes]:
                        time.sleep(1)
                    
                    print(f"✓ Index '{self.PINECONE_INDEX_NAME}' created successfully.")
                    
                except Exception as create_error:
                    print(f"✗ Failed to create index: {create_error}")
                    print("You may need to create the index manually in the Pinecone console.")
                    raise
            
            # Connect to index and get stats
            self.index = self.pc.Index(self.PINECONE_INDEX_NAME)
            index_stats = self.index.describe_index_stats()
            pinecone_dimension = index_stats.dimension
            
            print(f"✓ Pinecone index '{self.PINECONE_INDEX_NAME}' connected successfully.")
            print(f"Index stats: {index_stats}")
            
            # Check dimension compatibility
            if pinecone_dimension != self.EXPECTED_DIMENSION:
                print(f"⚠️  WARNING: Pinecone index dimension ({pinecone_dimension}) != expected dimension ({self.EXPECTED_DIMENSION})")
                # Update expected dimension to match Pinecone
                self.EXPECTED_DIMENSION = pinecone_dimension
                
        except Exception as e:
            print(f"✗ Failed to initialize Pinecone: {e}")
            raise
    
    def initialize_embedding_model(self):
        """Initialize the sentence transformer embedding model"""
        print(f"Loading Sentence Transformer model '{self.EMBEDDING_MODEL_NAME}'...")
        
        try:
            self.embedding_model = SentenceTransformer(self.EMBEDDING_MODEL_NAME)
            
            # Test the model and check dimension
            test_embedding = self.embedding_model.encode("test sentence")
            model_dimension = len(test_embedding)
            
            if model_dimension != self.EXPECTED_DIMENSION:
                print(f"⚠️  Model dimension ({model_dimension}) != expected ({self.EXPECTED_DIMENSION})")
                print("Updating expected dimension based on loaded model.")
                self.EXPECTED_DIMENSION = model_dimension
            
            print(f"✓ Embedding model loaded. Dimension: {self.EXPECTED_DIMENSION}")
            
        except Exception as e:
            print(f"✗ Failed to load embedding model: {e}")
            raise
    
    def initialize_text_splitter(self):
        """Initialize the text splitter"""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZE,
            chunk_overlap=self.CHUNK_OVERLAP,
            length_function=len,
            add_start_index=True,
        )
        print("✓ Text splitter initialized.")
    
    def initialize_all(self):
        """Initialize all components"""
        print("=== Initializing Services ===")
        self.setup_pdf_directory()
        self.initialize_pinecone()
        self.initialize_embedding_model()
        self.initialize_text_splitter()
        print("✓ All services initialized successfully.\n")
    
    def process_pdf(self, pdf_path):
        """Process a single PDF file and return vectors"""
        filename = os.path.basename(pdf_path)
        print(f"Processing '{filename}'...")
        
        try:
            reader = PdfReader(pdf_path)
            doc_chunks = []
            
            # Extract text page by page
            for i, page in enumerate(tqdm(reader.pages, desc=f"Reading pages from {filename}", leave=False)):
                page_text = page.extract_text()
                if page_text:
                    # Split page text into chunks
                    page_chunks = self.text_splitter.create_documents(
                        [page_text],
                        metadatas=[{"source": filename, "page": i + 1}]
                    )
                    
                    # Add metadata to each chunk
                    for chunk_doc in page_chunks:
                        cleaned_text = chunk_doc.page_content.replace('\n', ' ').strip()
                        chunk_doc.metadata['text_chunk'] = cleaned_text
                        chunk_doc.metadata['chunk_start_index'] = chunk_doc.metadata.get('start_index', -1)
                    
                    doc_chunks.extend(page_chunks)
            
            if not doc_chunks:
                print(f"⚠️  No text extracted from '{filename}'. Skipping.")
                return []
            
            print(f"Extracted {len(doc_chunks)} text chunks from '{filename}'.")
            
            # Generate embeddings
            print(f"Generating embeddings for {len(doc_chunks)} chunks...")
            chunk_texts = [chunk.metadata['text_chunk'] for chunk in doc_chunks]
            embeddings = self.embedding_model.encode(chunk_texts, show_progress_bar=False)
            
            # Prepare vectors for Pinecone
            vectors = []
            for i, chunk_doc in enumerate(doc_chunks):
                vector_id = f"{filename}_pg{chunk_doc.metadata['page']}_chk{i}"
                
                metadata_for_pinecone = {
                    "source_pdf": chunk_doc.metadata.get("source", "unknown"),
                    "page_number": chunk_doc.metadata.get("page", -1),
                    "chunk_start_index": chunk_doc.metadata.get("chunk_start_index", -1),
                    "text_chunk": chunk_doc.metadata.get("text_chunk", "")
                }
                
                vectors.append((
                    vector_id,
                    embeddings[i].tolist(),
                    metadata_for_pinecone
                ))
            
            print(f"✓ Prepared {len(vectors)} vectors from '{filename}'.")
            return vectors
            
        except Exception as e:
            print(f"✗ Error processing '{filename}': {e}")
            return []
    
    def upsert_vectors(self, all_vectors):
        """Upsert vectors to Pinecone in batches"""
        if not all_vectors:
            print("No vectors to upsert.")
            return 0
            
        print(f"Upserting {len(all_vectors)} vectors to Pinecone...")
        upserted_count = 0
        
        for i in tqdm(range(0, len(all_vectors), self.PINECONE_BATCH_SIZE), desc="Upserting batches"):
            batch = all_vectors[i:i + self.PINECONE_BATCH_SIZE]
            try:
                upsert_response = self.index.upsert(vectors=batch)
                upserted_count += upsert_response.upserted_count
            except Exception as e:
                print(f"✗ Error upserting batch starting at index {i}: {e}")
        
        print(f"✓ Total vectors upserted: {upserted_count}")
        return upserted_count
    
    def process_all_pdfs(self):
        """Main processing function"""
        print("=== Starting PDF Processing ===")
        
        # Get PDF files
        pdf_files = self.get_pdf_files()
        if not pdf_files:
            return
        
        # Process each PDF
        all_vectors = []
        for pdf_path in pdf_files:
            vectors = self.process_pdf(pdf_path)
            all_vectors.extend(vectors)
        
        print(f"\n=== Processing Complete. Total vectors prepared: {len(all_vectors)} ===")
        
        # Upsert to Pinecone
        if all_vectors:
            print("\n=== Upserting to Pinecone ===")
            self.upsert_vectors(all_vectors)
            
            # Final index stats
            try:
                print("\nFinal index stats:")
                print(self.index.describe_index_stats())
            except Exception as e:
                print(f"Could not retrieve final index stats: {e}")
        
        print("\n=== Process Complete ===")

def main():
    """Main execution function"""
    # Uncomment the line below if you need to install dependencies
    # install_dependencies()
    
    # Create processor instance
    processor = PDFToPinecone()
    
    # Print configuration
    processor.print_config()
    
    try:
        # Initialize all services
        processor.initialize_all()
        
        # Process all PDFs
        processor.process_all_pdfs()
        
    except Exception as e:
        print(f"✗ An error occurred: {e}")
        print("Please check your configuration and try again.")

if __name__ == "__main__":

    main()
