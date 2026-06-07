export default {
  common: {
    failed: '操作失敗',
    success: '操作成功',
  },
  navigation: {
    swap: '交換',
    explore: '探索',
    positions: '部位',
    trending: '熱門',
    docs: '文件',
  },
  header: {
    theme: '主題',
    language: '語言',
  },
  language: {
    english: 'English',
    traditionalChinese: '繁體中文',
    current: '目前語言',
  },
  faq: {
    title: '常見問題',
    items: [
      {
        question: 'Linera 上的 MicroMeme 是什麼？',
        answer:
          'MicroMeme 是一個建構在 Linera 上的迷因交易產品。它把迷因代幣建立、AMM 資金池建立、代幣交換、即時圖表、資金池探索、部位和交易紀錄整合在同一個介面中。',
      },
      {
        question: 'MicroMeme 如何使用 Linera microchains？',
        answer:
          'MicroMeme 以 Linera 應用和應用擁有的鏈為核心。迷因代幣、交換路由和資金池是彼此獨立的鏈上應用，透過 Linera 訊息協作，因此市場操作會在相關應用鏈和使用者鏈之間完成結算，而不是依賴單一大型合約。',
      },
      {
        question: '迷因代幣價格是怎麼計算的？',
        answer:
          '資金池使用類 Uniswap V2 的 constant product AMM 模型。畫面上的報價會根據目前池儲備、選定輸入數量和資金池交易費用計算；如果結算前池狀態改變，最終輸出仍可能變動。',
      },
      {
        question: '交換前應該檢查什麼？',
        answer:
          '確認交換前，請檢查代幣交易對、輸入和輸出數量、價格影響、滑價容忍度、資金池費用、預估 Linera 網路 gas，以及接收結果的錢包帳戶。',
      },
      {
        question: '為什麼圖表、餘額和交易紀錄會在結算後更新？',
        answer:
          'WebUI 採用事件驅動。鏈上事件被擷取、解碼、投影並推送到前端 store 後，市場資料才會刷新。錢包授權只是流程開始；相關資金池、交易和市場投影追上後，畫面狀態才算新鮮。',
      },
      {
        question: '如何建立迷因代幣？',
        answer:
          'Create Meme 流程讓支援的錢包設定名稱、ticker、logo、描述、初始供應量、小數位、社群連結、可選 mining 設定，以及初始流動性參數。啟用初始流動性時，發行流程可以同時建立第一個原生代幣資金池。',
      },
      {
        question: '什麼是 virtual initial liquidity？',
        answer:
          'Virtual initial liquidity 是迷因初始化流程中的發行期資金池參數。它會影響該 bootstrap 路徑的定價和池份額計算，但不是可領取的使用者餘額，也不能像普通流動性一樣被提取。',
      },
      {
        question: '部位裡的 LMM 是什麼？',
        answer:
          'LMM 是 MicroMeme 資金池鑄造出的流動性份額。它代表流動性提供者在類 V2 資金池中的池份額，不是另一個可交易的迷因代幣。Active 和 closed 部位由已記錄的加入流動性與移除流動性交易推導。',
      },
      {
        question: '為什麼資金有時會顯示為 claimable balances？',
        answer:
          '部分跨應用結果，例如交換輸出、移除流動性支付、退款或協議費提領，會在不能假設直接送達可靠時表示為可領取餘額。這讓可恢復價值保持明確，而不是隱藏在不可靠的推送轉帳後面。',
      },
      {
        question: 'MicroMeme 會保證獲利、獎勵或執行成功嗎？',
        answer:
          '不會。迷因代幣和流動性部位可能涉及價格波動、滑價、池曝險變化、專案自訂 mining 規則、錢包授權失敗或跨鏈結算延遲。簽署前請務必檢查交易細節。',
      },
    ],
  },
  transactions: {
    columns: {
      time: '時間',
      swap: '交換',
      value: '價值',
      bought: '買入',
      sold: '賣出',
      address: '地址',
    },
    action: {
      swap: '交換',
      for: '兌',
    },
    empty: {
      title: '沒有交易',
      caption: '交換結算後，交易會顯示在這裡。',
    },
  },
}
