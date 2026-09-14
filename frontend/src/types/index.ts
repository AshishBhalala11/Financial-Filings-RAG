export type SourceChunk = {
  chunk_id: string;
  content: string;
  page: number | null;
  section: string | null;
  source: string | null;
  retrieval_score: number | null;
  rerank_score: number | null;
};

export type RankedChunk = {
  chunk_id: string;
  page: number | null;
  section: string | null;
  snippet: string;
  score_type: "retrieval" | "rerank";
  score: number | null;
};

export type QueryResponse = {
  answer: string;
  sources: SourceChunk[];
  route_type: "lookup" | "multi_part" | "summarization";
  sub_queries: string[];
  document_id: string | null;
  pre_rerank: RankedChunk[];
  post_rerank: RankedChunk[];
};

export type UploadResponse = {
  message: string;
  document_id: string;
  filename: string;
  page_count: number;
  chunk_count: number;
};
