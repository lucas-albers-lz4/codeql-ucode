import { cursor } from 'uci';
function run() { let ctx = cursor(); ctx.commit('ok'); system('/etc/init.d/fixture restart >/dev/null 2>&1'); }
