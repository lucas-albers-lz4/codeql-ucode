import { readfile } from 'fs';
function local(readfile) { return readfile('unused'); }
printf('existing=%s\n', local(function(x) { return 'shadow'; }));
