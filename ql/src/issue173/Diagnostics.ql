import codeql.ucode.Diagnostics

from Diagnostic d
select d, d.getSeverity(), d.getTag(), d.getMessage(), d.getLocation()
