"""
Brains Service - AI intelligence layer powered by kluvs-reader

This service provides the bot's AI capabilities through the kluvs-reader SDK,
which handles RAG-powered questions, book summaries, and Socratic tutoring.
"""
import asyncio
from typing import Optional
from kluvs_reader import SocraticEngine


class BrainsService:
    """
    AI service wrapper for kluvs-reader's SocraticEngine.

    This service provides a Discord-bot-friendly async interface to the AI backend,
    handling RAG-powered questions about books using Socratic tutoring methodology.

    Attributes:
        engine: The underlying SocraticEngine from kluvs-reader
        default_scope: Hardcoded scope filter for the experimental phase
    """

    def __init__(self, supabase_url: str, supabase_key: str, openai_key: str):
        """
        Initialize the brains service with API credentials.

        Args:
            supabase_url: Supabase project URL for the brains backend
            supabase_key: Supabase API key for authentication
            openai_key: OpenAI API key for GPT and embeddings

        Raises:
            ValueError: If any required credentials are missing
        """
        if not all([supabase_url, supabase_key, openai_key]):
            raise ValueError("All API credentials required for BrainsService")

        self.engine = SocraticEngine(supabase_url, supabase_key, openai_key)

        # Hardcoded scope for experimental phase
        # TODO: Make this dynamic based on book/session data
        self.default_scope = "humanitarian_ai_experiment"

        print("[INFO] BrainsService initialized with experimental scope")

    async def ask(
        self,
        question: str,
        book_title: str,
        scope: Optional[str] = None
    ) -> str:
        """
        Ask a question about a book using RAG-powered Socratic tutoring.

        This method uses the SocraticEngine to search relevant book excerpts
        and generate a Socratic response with hints and follow-up questions.

        Args:
            question: The student's question about the book
            book_title: Title of the book being discussed
            scope: Optional scope filter for the RAG search
                  (defaults to hardcoded experimental scope)

        Returns:
            Socratic response with hints, context, and follow-up questions

        Raises:
            Exception: If the underlying AI service encounters an error

        Note:
            The SocraticEngine.ask() method is currently synchronous, so we
            wrap it in asyncio.to_thread() to avoid blocking the Discord event loop.
            TODO: Make SocraticEngine.ask() async in kluvs-reader
        """
        actual_scope = scope or self.default_scope

        print(f"[INFO] BrainsService.ask() called - Book: '{book_title}', Scope: '{actual_scope}'")

        try:
            # Wrap synchronous call in thread to avoid blocking Discord
            # TODO: Remove this wrapper once SocraticEngine.ask() becomes async
            response = await asyncio.to_thread(
                self.engine.ask,
                question,
                actual_scope,
                book_title
            )

            print(f"[SUCCESS] BrainsService.ask() completed for '{book_title}'")
            return response

        except Exception as e:
            # Let errors bubble up - bot's error handler will catch them
            print(f"[ERROR] BrainsService.ask() failed: {str(e)}")
            raise
