from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(text: str, source: str):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )

    chunks = splitter.split_text(text)

    structured_chunks = []

    for i, chunk in enumerate(chunks):
        structured_chunks.append({
            "content": chunk,
            "metadata": {
                "source": source,
                "chunk_id": i
            }
        })

    return structured_chunks