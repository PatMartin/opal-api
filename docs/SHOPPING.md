# OPAL Shopping Recipes

Twenty shopping and pantry workflows that chain multiple OPAL services
together — Look reads labels, shelves, and receipts; Listen captures
spoken list additions and questions; Think compares, plans, and
summarizes; Say speaks answers and reminders; and Event logs purchases
and inventory for the household record. Where COOKBOOK.md exercises one
service per recipe, these composite recipes pass results between them.

Every example is a fenced `bash` block so Markdown renderers such as GitHub
show a **Copy** button. Replace capitalized IDs (`VOICE_ID`, `CAMERA_ID`,
`PIPELINE_ID`, `OCR_PIPELINE`, ...) with values from your deployment, and
set these once per shell:

```bash
VOICE_ID=narrator                 # from: opal config voice list --json
CAMERA_ID=pantry-1                # from: opal look source list --json
OCR_PIPELINE=text-pipeline        # from: opal look info capabilities --json
PIPELINE_ID=detector-pipeline     # from: opal look info capabilities --json
```

Field notes used below: Listen results carry `transcript`, `intent_name`,
`matched`, `slot_values`; THINK tasks carry `.id` on create and `.answer`
once `completed`; Event requires `topic` and `data`.

## Contents

1. [Grocery Lists and Pantry](#1-grocery-lists-and-pantry)
2. [In-Store and Product Identification](#2-in-store-and-product-identification)
3. [Receipts, Prices, and Returns](#3-receipts-prices-and-returns)
4. [Meal Planning and Restock](#4-meal-planning-and-restock)

## 1. Grocery Lists and Pantry

### 1. Spoken item to the grocery list

Dictate an item and append it to the shared list.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file add-milk.wav --save-log true --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt 'Turn this spoken request into a short list entry.' \
  --context "{\"speech\":\"$TRANSCRIPT\"}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' >> grocery-list.txt
cat grocery-list.txt
```

### 2. Pantry photo inventory

Photograph a shelf and let THINK list what is running low.

```bash
opal look analyze image --image pantry.jpg --pipeline-id "$OCR_PIPELINE" --json > pantry.json
OBS=$(jq -c '.observations' pantry.json)
TID=$(opal think task create \
  --prompt 'List visible items that look nearly empty or missing from this pantry shelf.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > restock.txt
cat restock.txt
```

### 3. Read the list aloud before leaving

Hear the running grocery list spoken back for a final check.

```bash
ITEMS=$(cat grocery-list.txt)
TID=$(opal think task create \
  --prompt 'Read this grocery list aloud as a short spoken checklist.' \
  --context "{\"items\":\"$ITEMS\"}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file list-check.wav
```

### 4. Log a completed shopping trip

Publish the trip's item count as a dated event for the household record.

```bash
COUNT=$(wc -l < grocery-list.txt)
opal data event publish --topic shopping.trip \
  --source household --data "{\"items\":$COUNT}" --json
opal data event list --topic shopping.trip --limit 10 --json
```

### 5. Fridge contents check — what's already home

Snap the fridge and compare against the list to avoid double-buying.

```bash
opal look analyze image --image fridge.jpg --pipeline-id "$OCR_PIPELINE" --json > fridge.json
OBS=$(jq -c '.observations' fridge.json)
TID=$(opal think task create \
  --prompt 'From this fridge photo and my list, which items should I NOT buy because they are already stocked?' \
  --context "{\"observations\":$OBS,\"list\":\"$(cat grocery-list.txt)\"}" \
  --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer'
```

## 2. In-Store and Product Identification

### 6. Identify an unfamiliar product

Photograph an unknown item and hear what it likely is.

```bash
opal look analyze image --image product.jpg --pipeline-id "$PIPELINE_ID" --json > prod.json
OBS=$(jq -c '.observations' prod.json)
TID=$(opal think task create \
  --prompt 'Name this store product in one short phrase for a shopper.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file product-name.wav
```

### 7. Read a label aloud

OCR a package's nutrition or ingredients label and hear it read.

```bash
opal look analyze image --image label.jpg --pipeline-id "$OCR_PIPELINE" --json > label.json
TEXT=$(jq -r '.observations[0].text // .observations[0].label' label.json)
opal say generate --voice-id "$VOICE_ID" --text "Label says: $TEXT" \
  --output-format wav --output-file label.wav
```

### 8. Compare two products side by side

Photograph two labels and get a spoken plain-English comparison.

```bash
opal look analyze image --image label-a.jpg --pipeline-id "$OCR_PIPELINE" --json > a.json
opal look analyze image --image label-b.jpg --pipeline-id "$OCR_PIPELINE" --json > b.json
TID=$(opal think task create \
  --prompt 'Compare these two product labels for a shopper in two sentences.' \
  --context "{\"a\":$(jq -c '.observations' a.json),\"b\":$(jq -c '.observations' b.json)}" \
  --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file compare.wav
```

### 9. Spoken store question to text answer

Ask a store question aloud and get a text answer for the list.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file store-question.wav --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt "Answer this grocery-shopping question in one sentence: $TRANSCRIPT" \
  --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > store-answer.txt
cat store-answer.txt
```

### 10. Check for a recalled or allergen item

Photograph a package and ask THINK to flag common allergens before buying.

```bash
opal look analyze image --image snack.jpg --pipeline-id "$OCR_PIPELINE" --json > snack.json
OBS=$(jq -c '.observations' snack.json)
TID=$(opal think task create \
  --prompt 'Does this package label list peanuts, tree nuts, or gluten? Answer plainly.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file allergen.wav
```

## 3. Receipts, Prices, and Returns

### 11. Scan a receipt to a spending event

OCR the receipt and log the purchase total for the household ledger.

```bash
opal look analyze image --image receipt.jpg --pipeline-id "$OCR_PIPELINE" --json > r.json
TEXT=$(jq -r '.observations[0].text // .observations[0].label' r.json)
TID=$(opal think task create \
  --prompt 'Extract the store name and total from this receipt text.' \
  --context "{\"text\":\"$TEXT\"}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal data event publish --topic shopping.receipt \
  --source scanner --data "$(opal think task show "$TID" --json | jq -c '{receipt:.answer}')" --json
```

### 12. Price sanity check — is this a good deal?

Speak a shelf price and let THINK judge whether it is reasonable.

```bash
TRANSCRIPT=$(opal listen recognition test-text --text 'is eight dollars a good price for a gallon of milk?' --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt "Answer yes or no with a one-line reason: $TRANSCRIPT" \
  --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file deal.wav
```

### 13. Return window tracker — log the purchase date

Save the receipt date as an event so the return deadline is recorded.

```bash
opal look analyze image --image return-receipt.jpg --pipeline-id "$OCR_PIPELINE" --json > rr.json
TEXT=$(jq -r '.observations[0].text // .observations[0].label' rr.json)
opal data event publish --topic shopping.return \
  --source receipts --data "{\"receipt\":\"$TEXT\"}" --json
```

### 14. Warranty card capture

Photograph a warranty card or serial number for the file.

```bash
opal look analyze image --image warranty.jpg --pipeline-id "$OCR_PIPELINE" --json > w.json
TEXT=$(jq -r '.observations[0].text // .observations[0].label' w.json)
opal data event publish --topic shopping.warranty \
  --source receipts --data "{\"card\":\"$TEXT\"}" --json
```

### 15. Monthly spend digest — receipts to a spoken summary

Summarize the month's receipt events aloud.

```bash
opal data event list --topic shopping.receipt --limit 30 --json > month.json
TID=$(opal think task create \
  --prompt 'Summarize this month of receipts in two sentences for the household.' \
  --context "$(jq -c '{items:.items}' month.json)" \
  --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file spend-digest.wav
```

## 4. Meal Planning and Restock

### 16. Pantry-to-dinner suggestion

Photograph the pantry and ask what could be made tonight.

```bash
opal look analyze image --image pantry-dinner.jpg --pipeline-id "$OCR_PIPELINE" --json > din.json
OBS=$(jq -c '.observations' din.json)
TID=$(opal think task create \
  --prompt 'Suggest one dinner I could make from these pantry items, in one sentence.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file dinner-idea.wav
```

### 17. Recipe to shopping list

Hand THINK a recipe photo and get a missing-ingredients list back.

```bash
opal look analyze image --image recipe.jpg --pipeline-id "$OCR_PIPELINE" --json > rec.json
TEXT=$(jq -r '.observations[0].text // .observations[0].label' rec.json)
TID=$(opal think task create \
  --prompt 'List the ingredients from this recipe I likely need to buy.' \
  --context "{\"recipe\":\"$TEXT\",\"pantry\":\"$(cat restock.txt 2>/dev/null)\"}" \
  --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' >> grocery-list.txt
```

### 18. Voice restock — spoken item to pantry event

Say what was just used up; it becomes a restock signal.

```bash
TRANSCRIPT=$(opal listen recognition test-text --text 'we are out of eggs' --json | jq -r '.transcript')
opal data event publish --topic shopping.restock \
  --source kitchen-voice --data "{\"item\":\"$TRANSCRIPT\"}" --json
opal data event list --topic shopping.restock --limit 10 --json
```

### 19. Leftover rescue — what to cook with what's left

Photograph the fridge leftovers and get a use-it-up suggestion.

```bash
opal look analyze image --image leftovers.jpg --pipeline-id "$OCR_PIPELINE" --json > left.json
OBS=$(jq -c '.observations' left.json)
TID=$(opal think task create \
  --prompt 'Suggest one dish to use up these leftovers, in one sentence.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file leftover.wav
```

### 20. Weekly grocery plan — list to spoken plan

Turn the week's list into a brief spoken plan grouped by store section.

```bash
ITEMS=$(cat grocery-list.txt)
TID=$(opal think task create \
  --prompt 'Group this grocery list by store section and read it as a two-minute plan.' \
  --context "{\"items\":\"$ITEMS\"}" --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file shop-plan.wav
```

## Practical Notes

- **Chain with `jq`.** Extract `transcript`, `.id`, `.answer`,
  `.observations`, and `.matched` explicitly; do not assume field order.
- **Keep lists append-only.** Dictated items and OCR'd receipts both write
  to the same files or topics — review before clearing.
- **Label photos.** Receipts, labels, and pantry shots all pass through
  `analyze image`; keep filenames descriptive for later review.
- **Confirm before buying.** A label verdict or price check is an aid, not
  a guarantee — verify allergens and expiry dates yourself.
- **Replace IDs, not semantics.** Any shelf camera, pipeline, or voice ID
  works; adapt topics and contexts to your household.
