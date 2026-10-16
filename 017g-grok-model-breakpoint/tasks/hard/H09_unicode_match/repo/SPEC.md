# Token match

`match.matches(query, text)` is true when every query token occurs in the text. Order does not matter. Extra text tokens are fine.

Token rules, shared by query and text:

- Split on whitespace only. A hyphenated word is one token. `state` does not match `state-of-the-art`.
- Strip leading and trailing `.,;:!?"'\`()[]{}` from each token. A trailing comma must not keep two equal words apart.
- Then Unicode-casefold and NFC-normalize. `café` matches `Cafe` plus a combining acute accent. `straße` matches `STRASSE`.

`normalize.normalize_token` and `tokens.tokenize` own those steps. `match.matches` must use them.

The visible test is the `café` case only.
