# Small-input JSON-value-stream contract, not a full JSONL or EVE schema.
# Invocation: jq -e -s -f validate_status.jq INPUT
length > 0 and all(.[];
  if type != "object" then false
  elif (.status | type) != "number" then false
  else .status >= 100 and .status <= 599 and (.status | floor) == .status
  end
)