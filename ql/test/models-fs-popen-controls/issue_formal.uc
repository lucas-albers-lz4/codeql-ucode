import { popen } from 'fs';
function local(popen) { return popen('unused'); }
print(local(function(x) { return 'shadow'; }), '\n');
