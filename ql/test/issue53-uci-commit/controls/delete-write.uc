import { cursor } from 'uci';
function run() { let ctx = cursor(); delete ctx['commit']; ctx.commit('ok'); }
