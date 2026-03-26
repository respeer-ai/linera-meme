const assetUrl = (name: string) => new URL(`./${name}`, import.meta.url).href

const laughPng = assetUrl('Laugh.png')
const metaMaskSvg = assetUrl('MetaMask.svg')
const cheCkoPng = assetUrl('CheCko.png')

export { laughPng, metaMaskSvg, cheCkoPng }
