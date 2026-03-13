import md5 from 'md5'

export function hexMd5(s: string): string {
  return md5(s)
}
