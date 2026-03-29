class RagService:
    def __init__(
        self,
        retriever,
        reranker,
        generator
    ):
        self.retriever = retriever
        self.reranker = reranker
        self.generator = generator

    def run(self, query: str):
        # Step 1: Retrieval
        docs = self.retriever.retrieve(query)

        # Step 2: Reranking
        reranked_docs = self.reranker.rerank(query, docs)

        # Step 3: Context Building + Generation
        result = self.generator.generate(
            query=query,
            documents=reranked_docs
        )

        return result