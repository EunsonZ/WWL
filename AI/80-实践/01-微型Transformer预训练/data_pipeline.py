"""Pure-standard-library corpus, tokenizer, and packing utilities.

The tokenizer is deliberately small: a Unicode-character vocabulary fitted on
train documents only.  It is a teaching tokenizer, not a production choice.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SPECIAL_TOKENS = ("<pad>", "<unk>", "<bos>", "<eos>")


@dataclass(frozen=True)
class Document:
    document_id: str
    split: str
    rights: str
    text: str


def canonical_text(text: str) -> str:
    """Normalize only line endings and surrounding whitespace for leak checks."""

    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_corpus(path: Path) -> list[Document]:
    documents: list[Document] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw_line.strip():
            continue
        try:
            record = json.loads(raw_line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSON on corpus line {line_number}: {error}") from error
        required = {"id", "split", "rights", "text"}
        if set(record) != required or not all(isinstance(record[key], str) for key in required):
            raise ValueError(f"corpus line {line_number} must contain exactly string fields {sorted(required)}")
        documents.append(
            Document(
                document_id=record["id"],
                split=record["split"],
                rights=record["rights"],
                text=canonical_text(record["text"]),
            )
        )
    validate_corpus(documents)
    return documents


def validate_corpus(documents: list[Document]) -> None:
    if not documents:
        raise ValueError("corpus is empty")
    allowed_splits = {"train", "dev", "test"}
    ids: set[str] = set()
    split_hashes: dict[str, set[str]] = {split: set() for split in allowed_splits}
    for document in documents:
        if document.document_id in ids:
            raise ValueError(f"duplicate document id: {document.document_id}")
        ids.add(document.document_id)
        if document.split not in allowed_splits:
            raise ValueError(f"invalid split for {document.document_id}: {document.split}")
        if document.rights != "created-for-this-tutorial":
            raise ValueError(f"unapproved rights marker for {document.document_id}")
        if not document.text:
            raise ValueError(f"empty text for {document.document_id}")
        text_hash = sha256_text(document.text)
        for other_split, other_hashes in split_hashes.items():
            if other_split != document.split and text_hash in other_hashes:
                raise ValueError(
                    f"exact normalized text leak: {document.document_id} duplicates {other_split}"
                )
        split_hashes[document.split].add(text_hash)
    missing = allowed_splits - {document.split for document in documents}
    if missing:
        raise ValueError(f"missing corpus splits: {sorted(missing)}")


def documents_for_split(documents: Iterable[Document], split: str) -> list[Document]:
    selected = [document for document in documents if document.split == split]
    if not selected:
        raise ValueError(f"split has no documents: {split}")
    return selected


class CharTokenizer:
    """A deterministic Unicode-character tokenizer fitted on train text only."""

    def __init__(self, tokens: list[str]):
        if tokens[: len(SPECIAL_TOKENS)] != list(SPECIAL_TOKENS):
            raise ValueError("special token ids must be pad=0, unk=1, bos=2, eos=3")
        if len(tokens) != len(set(tokens)):
            raise ValueError("token vocabulary contains duplicates")
        self.tokens = tokens
        self.token_to_id = {token: index for index, token in enumerate(tokens)}

    @classmethod
    def fit(cls, train_documents: Iterable[Document]) -> "CharTokenizer":
        characters = sorted({character for document in train_documents for character in document.text})
        if not characters:
            raise ValueError("cannot fit tokenizer on empty train text")
        return cls(list(SPECIAL_TOKENS) + characters)

    @property
    def pad_id(self) -> int:
        return 0

    @property
    def unk_id(self) -> int:
        return 1

    @property
    def bos_id(self) -> int:
        return 2

    @property
    def eos_id(self) -> int:
        return 3

    def encode(self, text: str, *, add_boundaries: bool = False) -> list[int]:
        ids = [self.token_to_id.get(character, self.unk_id) for character in text]
        return [self.bos_id, *ids, self.eos_id] if add_boundaries else ids

    def decode(self, ids: Iterable[int], *, skip_special: bool = True) -> str:
        output: list[str] = []
        for token_id in ids:
            if not 0 <= token_id < len(self.tokens):
                raise ValueError(f"token id out of range: {token_id}")
            token = self.tokens[token_id]
            if token in SPECIAL_TOKENS:
                if not skip_special:
                    output.append(token)
            else:
                output.append(token)
        return "".join(output)

    def to_dict(self) -> dict[str, object]:
        return {"type": "unicode-character-v1", "tokens": self.tokens}

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "CharTokenizer":
        if payload.get("type") != "unicode-character-v1":
            raise ValueError("unsupported tokenizer type")
        tokens = payload.get("tokens")
        if not isinstance(tokens, list) or not all(isinstance(token, str) for token in tokens):
            raise ValueError("invalid tokenizer token list")
        return cls(tokens)

    def fingerprint(self) -> str:
        serialized = json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return sha256_text(serialized)


def pack_documents(
    documents: Iterable[Document],
    tokenizer: CharTokenizer,
    block_size: int,
) -> list[list[int]]:
    """Pack BOS/text/EOS streams into block_size+1 chunks for next-token pairs.

    Documents can attend across an EOS boundary.  This matches a simple
    continuous-corpus pretraining stream and is documented as such in the lab.
    The final chunk is padded; pad targets are excluded from loss.
    """

    if block_size < 2:
        raise ValueError("block_size must be at least 2")
    stream: list[int] = []
    for document in documents:
        stream.extend(tokenizer.encode(document.text, add_boundaries=True))
    width = block_size + 1
    # Adjacent next-token examples overlap by one token: the final target of a
    # block is the first input of the next block.  Advancing by ``width`` would
    # silently drop the target immediately after every block boundary.
    blocks = [
        stream[start : start + width]
        for start in range(0, len(stream) - 1, block_size)
    ]
    if not blocks:
        raise ValueError("cannot pack an empty document stream")
    if len(blocks[-1]) < width:
        blocks[-1].extend([tokenizer.pad_id] * (width - len(blocks[-1])))
    return blocks


def shuffled_blocks(blocks: list[list[int]], seed: int) -> list[list[int]]:
    copied = [list(block) for block in blocks]
    random.Random(seed).shuffle(copied)
    return copied


def block_fingerprint(blocks: list[list[int]]) -> str:
    serialized = json.dumps(blocks, separators=(",", ":"))
    return sha256_text(serialized)
