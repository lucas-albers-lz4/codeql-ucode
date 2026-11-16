/** Raw second-name calls; independent of helper target resolution. */
import codeql.ucode.m3.Models

from NamedCall call
where call.getName() = "localHelper"
select call
