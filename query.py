# query.py

import os
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

class DocumentChat:
    def __init__(self):
        # --- Configuration ---
        # Ensure these match your upload script's configuration
        self.PINECONE_API_KEY = "pcsk_6jWP9D_PNZsPKs6wfdaKuuPGParHANpumiSTB5inUqdt1TVYUwKoYyD1g9dhdq8GtCjz6M" # <--- EDIT THIS
        self.PINECONE_INDEX_NAME = "scai-index"
        self.EMBEDDING_MODEL_NAME = 'intfloat/multilingual-e5-large'
        
        # You need a Google AI Studio API key for Gemini
        self.GEMINI_API_KEY = "AIzaSyCZFc_xT3Y4lGsFiUompQ8Lhaf-tjSaKgs" # <--- EDIT THIS

        # --- Initialize Components ---
        self.pinecone_index = None
        self.embedding_model = None
        self.generative_model = None
        
        # Run initialization
        self.initialize_all()

    def initialize_all(self):
        """Initializes all necessary services."""
        print("=== Initializing Services ===")
        
        # 1. Initialize Pinecone
        try:
            pc = Pinecone(api_key=self.PINECONE_API_KEY)
            self.pinecone_index = pc.Index(self.PINECONE_INDEX_NAME)
            print(f"✓ Pinecone index '{self.PINECONE_INDEX_NAME}' connected.")
        except Exception as e:
            print(f"✗ Failed to connect to Pinecone: {e}")
            raise

        # 2. Initialize Embedding Model (must be the same as the upload script)
        try:
            self.embedding_model = SentenceTransformer(self.EMBEDDING_MODEL_NAME)
            print(f"✓ Embedding model '{self.EMBEDDING_MODEL_NAME}' loaded.")
        except Exception as e:
            print(f"✗ Failed to load embedding model: {e}")
            raise
            
        # 3. Initialize Google Gemini
        try:
            genai.configure(api_key=self.GEMINI_API_KEY)
            self.generative_model = genai.GenerativeModel('gemini-1.5-flash')
            print("✓ Google Gemini model loaded.")
        except Exception as e:
            print(f"✗ Failed to initialize Gemini: {e}")
            print("Please ensure you have a valid GEMINI_API_KEY.")
            raise

        print("=== All services initialized successfully. ===")

    def get_answer(self, query: str):
        """
        Retrieves context from Pinecone and generates an answer using Gemini.
        """
        if not all([self.pinecone_index, self.embedding_model, self.generative_model]):
            print("Services not initialized. Cannot get answer.")
            return

        # 1. RETRIEVE: Create an embedding for the user's query
        print(f"\n1. Creating embedding for the query: '{query}'")
        query_embedding = self.embedding_model.encode(query).tolist()

        # 2. RETRIEVE: Query Pinecone to find the most relevant text chunks
        print("2. Querying Pinecone for relevant context...")
        query_results = self.pinecone_index.query(
            vector=query_embedding,
            top_k=5,  # Retrieve the top 5 most relevant chunks
            include_metadata=True
        )

        # Extract the text from the metadata of the results
        context = ""
        if query_results['matches']:
            for match in query_results['matches']:
                text_chunk = match['metadata'].get('text_chunk', '')
                source_pdf = match['metadata'].get('source_pdf', 'Unknown source')
                page_number = match['metadata'].get('page_number', 'N/A')
                context += f"- {text_chunk} (Source: {source_pdf}, Page: {page_number})\n"
        else:
            print("No relevant context found in Pinecone.")
            return "I'm sorry, but I couldn't find any information related to your question in the documents."

        # 3. AUGMENT: Create the prompt for the LLM
        prompt_template = f"""
        You are an expert assistant who answers questions based ONLY on the provided context.
        Your task is to synthesize the information from the context below to answer the user's question.
        Do not use any external knowledge. If the answer is not contained within the text below, say "I'm sorry, but I couldn't find information on this topic in the provided documents."

        CONTEXT:
        {context}

        USER'S QUESTION:
        {query}

        ANSWER:
        """
        
        print("3. Sending augmented prompt to Gemini for answer generation...")
        
        # 4. GENERATE: Send the prompt to Gemini and get the answer
        try:
            response = self.generative_model.generate_content(prompt_template)
            return response.text
        except Exception as e:
            print(f"✗ Error during Gemini generation: {e}")
            return "An error occurred while generating the answer."


def main():
    """
    Main function to run the chat application.
    """
    chat_app = DocumentChat()
    
    print("\n--- AI Document Assistant ---")
    print("Ask a question about your documents. Type 'exit' to quit.")
    
    while True:
        user_query = input("\nYour question: ")
        if user_query.lower() == 'exit':
            break
        
        answer = chat_app.get_answer(user_query)
        print("\n--- Answer ---")
        print(answer)
        print("----------------")

if __name__ == "__main__":
    main()