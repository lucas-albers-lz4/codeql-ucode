import * as fs from 'fs';
fs.stat('/etc/ssl/certs/ca-certificates.crt');
fs.rename('/old', '/new');
