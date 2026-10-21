// TOTP (RFC 6238; SHA-1, 6 digits, 30-second step, as apps/api/qms_os/auth/totp.py) for the synthetic account the
// test-only bootstrap creates. Web Crypto only; no dependency.
const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

function base32(secret: string): Uint8Array<ArrayBuffer> {
  let bits = 0;
  let value = 0;
  const out: number[] = [];
  for (const ch of secret.replace(/=+$/, "").toUpperCase()) {
    const index = ALPHABET.indexOf(ch);
    if (index < 0) {
      throw new Error("not a base32 secret");
    }
    value = (value << 5) | index;
    bits += 5;
    if (bits >= 8) {
      out.push((value >>> (bits - 8)) & 0xff);
      bits -= 8;
    }
  }
  return new Uint8Array(out);
}

export function totpStep(atMs: number = Date.now()): number {
  return Math.floor(atMs / 1000 / 30);
}

export async function totp(secret: string, atMs: number = Date.now()): Promise<string> {
  const key = await crypto.subtle.importKey("raw", base32(secret), { name: "HMAC", hash: "SHA-1" }, false, ["sign"]);
  const counter = new DataView(new ArrayBuffer(8));
  counter.setBigUint64(0, BigInt(totpStep(atMs)));
  const mac = new Uint8Array(await crypto.subtle.sign("HMAC", key, counter.buffer));
  const offset = (mac[mac.length - 1] ?? 0) & 0x0f;
  const word = new DataView(mac.buffer).getUint32(offset) & 0x7fffffff;
  return String(word % 1_000_000).padStart(6, "0");
}
