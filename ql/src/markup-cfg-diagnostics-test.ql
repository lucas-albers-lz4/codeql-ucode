import codeql.ucode.Diagnostics
from Diagnostic d
select d.getLocation().getFile().getBaseName(), d.getTag(), d.getMessage()
