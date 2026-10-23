# Manila Multimodal RAG

This pipeline creates a separate evidence and review dataset for building reconstruction. It does **not** write to `Manila/vector-tiles/*.pbf` or modify `manila.html`.

## Pipeline stages

1. **Repository retrieval:** indexes relevant committed CSV, JSON, JSONL and GeoJSON records, then retrieves spatially close records (and exact matching IDs where available).
2. **External evidence retrieval:** queries public KartaView imagery metadata, Wikimedia Commons geosearch (including image URLs and license/attribution metadata), and Wikipedia geosearch near each tile's building center. Image evidence is re-ranked by distance to each building.
3. **Vision model:** when `OPENAI_API_KEY` is configured, a vision-capable model describes visible facade/roof/sign evidence and explicitly assesses whether the photo actually matches the target building.
4. **Evidence reconciliation model:** a separate model reconciles mapped properties, local records, image observations and source provenance. It labels proposed values as verified, inferred, conflicting or unknown and flags records needing human review.
5. **Durable checkpoints:** output records and progress are committed to `main` every ten newly processed buildings, then the pipeline resumes from existing records. The original PBF geometry is hashed for audit and never rewritten.

## Outputs

- `Manila/3d-rag/building-evidence.jsonl` — one evidence/RAG record per building feature.
- `Manila/3d-rag/retrieval-catalog.jsonl` — local source records used by retrieval.
- `Manila/3d-rag/progress-report.json` — progress, model usage, image/evidence counts, review flags and error summary.

## Model configuration

The workflow reads the repository secret `OPENAI_API_KEY`. Configure it in **GitHub → Settings → Secrets and variables → Actions** to enable the vision and synthesis stages. Without this secret, the workflow still performs repository/external evidence retrieval and writes source-linked records, but reports `evidence_retrieval_only_no_OPENAI_API_KEY`; it must not be described as having completed model-based multimodal RAG.

Default models are `gpt-4.1-mini` for visual analysis and `gpt-4.1` for evidence reconciliation. These can be overridden with `RAG_VISION_MODEL` and `RAG_SYNTHESIS_MODEL`. Visual analysis is capped at 150 buildings per run by default; synthesis runs for each newly processed building when the key is present. Review this cap and API usage before increasing it.

## Important limitations

- A nearby photo is only a candidate; distance does not prove building identity.
- Wikipedia search results and Wikimedia media metadata are contextual evidence, not automatic proof of a facade feature.
- The model may propose attributes only with evidence references; low-confidence and conflicting facts require review.
- Google imagery is not scraped or downloaded. Use only sources with an appropriate access path and respect their terms/licensing.
- This pipeline generates an evidence/review dataset. It does not itself create final facade meshes, roof geometry or sign decals, and does not automatically apply proposed values to source PBF tiles.
- The GitHub Actions workflow shares the existing `manila-3d-enrichment` concurrency group and waits rather than cancelling an active Manila run.
