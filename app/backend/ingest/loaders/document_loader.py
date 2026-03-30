import logging
from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class DocumentLoader:
    """Loads text files from a directory and splits them into overlapping chunks."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        glob: str = "**/*.txt",
    ) -> None:
        self._glob = glob
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )

    def load_and_split(self, directory: str) -> list:
        """Load all matching files from *directory* and return split chunks."""
        path = Path(directory)
        if not path.exists():
            raise FileNotFoundError(
                f"Knowledge base directory not found: {directory!r}"
            )

        logger.info("Loading documents from '%s' (glob: %s)…", directory, self._glob)
        loader = DirectoryLoader(
            str(path),
            glob=self._glob,
            loader_cls=TextLoader,
            show_progress=True,
            use_multithreading=True,
        )
        documents = loader.load()

        if not documents:
            raise ValueError(
                f"No documents matched glob '{self._glob}' in '{directory}'. "
                "Add .txt files to the knowledge_base directory and retry."
            )

        logger.info("Loaded %d raw document(s).", len(documents))
        chunks = self._splitter.split_documents(documents)
        logger.info("Split into %d chunk(s).", len(chunks))
        return chunks
