-- The application relies on true cosine-nearest-neighbor retrieval. No table-scan fallback.
CREATE OR REPLACE FUNCTION match_knowledge_chunks(
    query_embedding vector(1536),
    match_count INTEGER DEFAULT 5,
    filter_category TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    chunk_index INTEGER,
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ,
    similarity DOUBLE PRECISION
)
LANGUAGE SQL
STABLE
SET search_path = pg_catalog, public, pg_temp
AS $$
    SELECT chunk.id,
           chunk.document_id,
           chunk.chunk_index,
           chunk.content,
           chunk.metadata,
           chunk.created_at,
           1 - (chunk.embedding <=> query_embedding) AS similarity
    FROM public.knowledge_chunks AS chunk
    JOIN public.knowledge_documents AS document
      ON document.id = chunk.document_id
    WHERE chunk.embedding IS NOT NULL
      AND document.status = 'ACTIVE'
      AND (filter_category IS NULL OR document.category = filter_category)
    ORDER BY chunk.embedding <=> query_embedding
    LIMIT greatest(1, least(match_count, 50));
$$;

REVOKE ALL ON FUNCTION match_knowledge_chunks(vector, INTEGER, TEXT) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION match_knowledge_chunks(vector, INTEGER, TEXT) TO authenticated, service_role;
