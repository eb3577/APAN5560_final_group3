"""Run FAISS search outside the PyTorch process."""

import json
import sys

import faiss
import numpy as np


def main():
    path, vectors_path, top_k = sys.argv[1:]
    index = faiss.read_index(path)
    matrix = np.load(vectors_path, allow_pickle=False)
    if (not isinstance(index, faiss.IndexFlatIP)
            or (index.ntotal, index.d) != matrix.shape
            or not np.array_equal(index.reconstruct_n(0, index.ntotal), matrix)):
        raise SystemExit("FAISS index does not match the saved vectors. Rebuild it.")
    query = np.asarray([json.load(sys.stdin)], dtype=np.float32)
    scores, rows = index.search(query, int(top_k))
    print(json.dumps(list(zip(scores[0].tolist(), rows[0].tolist()))))


if __name__ == "__main__":
    main()
