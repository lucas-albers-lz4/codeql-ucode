#!/usr/bin/env bash
# Experimental template call-argument API and identity/CFG controls only.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
cd "$ROOT"
SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-template-call-arguments"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"

if [[ ! -x "$PACK/tools/osx64/extractor" && ! -x "$PACK/tools/linux64/extractor" ]]; then
	bash scripts/create-extractor-pack.sh
fi
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs

for query in TemplateCallArgumentRows TemplateLiteralPartRows TemplateSubstitutionRows TemplateSubstitutionExpressionScope TemplateCfgContract TemplateSubstitutionCfgOrder TemplateValueCfgMembership TemplateCfgNodes TemplateNoValueFlow; do
	codeql query compile "$ROOT/ql/src/extractor-smoke/$query.ql" --search-path="$QLPATH"
done

rm -rf "$DB"
mkdir -p .codeql-database
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode \
	--include='**/rpcd/ucode/luci' --include='**/template_args.uc' \
	--working-dir="$SRC" "$DB"
codeql database finalize "$DB"

source "$ROOT/scripts/m4-smoke-diagnostics.sh"
check_m4_extraction "$SRC/usr/share/rpcd/ucode/luci" "$SRC/template_args.uc"

for entry in \
	'TemplateCallArgumentRows args' \
	'TemplateLiteralPartRows literals' \
	'TemplateSubstitutionRows substitutions' \
	'TemplateSubstitutionExpressionScope expression_scope' \
	'TemplateCfgContract cfg' \
	'TemplateSubstitutionCfgOrder cfg_order' \
	'TemplateValueCfgMembership template_cfg' \
	'TemplateCfgNodes cfg_nodes' \
	'TemplateNoValueFlow no_value_flow'; do
	read -r query output <<< "$entry"
	codeql query run "$ROOT/ql/src/extractor-smoke/$query.ql" --database="$DB" --search-path="$QLPATH" --output="$DB/$output.bqrs"
	codeql bqrs decode --format=csv "$DB/$output.bqrs" > "$DB/$output.csv"
done

python3 - <<'PY'
import csv
import sys
from pathlib import Path

db = Path('.codeql-database/m4-template-call-arguments')
def messages(name):
    with (db / f'{name}.csv').open(newline='') as f:
        rows = list(csv.reader(f))
    return [row[1] for row in rows[1:]]

args = messages('args')
required_args = [
    'popen template arg 0 at 343:22-343:87 in usr/share/rpcd/ucode/luci',
    'system template arg 0 at 474:20-474:95 in usr/share/rpcd/ucode/luci',
    'popen template arg 0 at 3:28-3:41 in template_args.uc',
    'popen template arg 0 at 4:20-4:55 in template_args.uc',
    'system template arg 0 at 5:26-5:105 in template_args.uc',
    'system template arg 1 at 6:37-6:60 in template_args.uc',
]
if sorted(args) != sorted(required_args):
    sys.exit(f'template argument rows differ from the exact fixture multiset: {args}')

literals = messages('literals')
required_literals = [
    'literal fragment at 3:29-3:40 in template_args.uc',
    'literal fragment at 4:21-4:27 in template_args.uc',
    'literal fragment at 4:48-4:54 in template_args.uc',
    'literal fragment at 5:27-5:33 in template_args.uc',
    'literal fragment at 5:54-5:61 in template_args.uc',
    'literal fragment at 5:99-5:104 in template_args.uc',
    'literal fragment at 6:38-6:43 in template_args.uc',
    'literal fragment at 343:23-343:35 in usr/share/rpcd/ucode/luci',
    'literal fragment at 343:70-343:86 in usr/share/rpcd/ucode/luci',
    'literal fragment at 474:21-474:26 in usr/share/rpcd/ucode/luci',
    'literal fragment at 474:31-474:46 in usr/share/rpcd/ucode/luci',
    'literal fragment at 474:51-474:74 in usr/share/rpcd/ucode/luci',
    'literal fragment at 474:79-474:94 in usr/share/rpcd/ucode/luci',
]
if sorted(literals) != sorted(required_literals):
    sys.exit(f'literal fragment rows differ from the exact fixture multiset: {literals}')

substitutions = messages('substitutions')
required_substitutions = [
    'popen arg 0 template 343:22; substitution 0 at 343:36-343:69 in usr/share/rpcd/ucode/luci',
    'system arg 0 template 474:20; substitution 0 at 474:27-474:30 in usr/share/rpcd/ucode/luci',
    'system arg 0 template 474:20; substitution 1 at 474:47-474:50 in usr/share/rpcd/ucode/luci',
    'system arg 0 template 474:20; substitution 2 at 474:75-474:78 in usr/share/rpcd/ucode/luci',
    'popen arg 0 template 4:20; substitution 0 at 4:28-4:47 in template_args.uc',
    'system arg 0 template 5:26; substitution 0 at 5:34-5:53 in template_args.uc',
    'system arg 0 template 5:26; substitution 1 at 5:62-5:98 in template_args.uc',
    'system arg 1 template 6:37; substitution 0 at 6:44-6:59 in template_args.uc',
]
if sorted(substitutions) != sorted(required_substitutions):
    sys.exit(f'substitution rows differ from the exact fixture multiset: {substitutions}')

expression_scope = messages('expression_scope')
if expression_scope:
    sys.exit(f'expression wrapper escaped its template substitution child scope: {expression_scope}')

cfg = messages('cfg')
required_cfg = [
    'substitution expression CallExpression at 343:38-343:68 has exact CFG node',
    'substitution expression Identifier at 474:29-474:29 has exact CFG node',
    'substitution expression Identifier at 474:49-474:49 has exact CFG node',
    'substitution expression Identifier at 474:77-474:77 has exact CFG node',
    'substitution expression CallExpression at 4:30-4:46 has exact CFG node',
    'substitution expression CallExpression at 5:36-5:52 has exact CFG node',
    'substitution expression CallExpression at 5:64-5:97 has exact CFG node',
    'substitution expression CallExpression at 6:46-6:58 has exact CFG node',
]
if sorted(cfg) != sorted(required_cfg):
    sys.exit(f'canonical substitution/CFG identity rows differ: {cfg}')

cfg_order = messages('cfg_order')
required_cfg_order = [
    'source-order CFG path 0 -> 1 at 5 in template_args.uc',
    'source-order CFG path 0 -> 1 at 474 in usr/share/rpcd/ucode/luci',
    'source-order CFG path 0 -> 2 at 474 in usr/share/rpcd/ucode/luci',
    'source-order CFG path 1 -> 2 at 474 in usr/share/rpcd/ucode/luci',
]
if sorted(cfg_order) != sorted(required_cfg_order):
    sys.exit(f'substitution evaluation CFG order differs from source order: {cfg_order}')

template_cfg = messages('template_cfg')
if template_cfg:
    sys.exit(f'template construction unexpectedly has a value CFG node: {template_cfg}')

cfg_nodes = messages('cfg_nodes')
required_cfg_nodes = [
    'template AstCfgNode at 3:28 incoming and outgoing',
    'template AstCfgNode at 4:20 incoming and outgoing',
    'template AstCfgNode at 5:26 incoming and outgoing',
    'template AstCfgNode at 6:37 incoming and outgoing',
    'template AstCfgNode at 343:22 incoming and outgoing',
    'template AstCfgNode at 474:20 incoming and outgoing',
]
if len(cfg_nodes) != 6 or any(cfg_nodes.count(row) != 1 for row in required_cfg_nodes):
    sys.exit(f'expected each concrete template to be one ordered non-value CFG node: {cfg_nodes}')

no_value_flow = messages('no_value_flow')
if no_value_flow:
    sys.exit(f'found a value-preserving edge from a substitution to the constructed string: {no_value_flow}')

print('template argument identities and positions: exact positive/negative controls passed')
print('substitution identities/order and exact expression CFG identity: exact controls passed')
print('template strings: ordered AstCfgNodes, no value ExprNode, no substitution-to-string value edge')
PY
