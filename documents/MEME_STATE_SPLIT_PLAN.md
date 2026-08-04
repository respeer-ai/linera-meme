# Meme State App 拆分方案（草案）

## 1. 设计原则

- **不共享 state app ApplicationId**：每个 meme 有自己独立的 state app。
- **共享 state app ModuleId**：所有 meme state app 使用同一份 wasm bytecode（`meme_state_bytecode_id`），只需 publish 一次。
- **对齐 AMS / Blob-Gateway**：business app 维护 `state_applications` 索引，state app 存储实际数据。
- **Proxy 负责创建**：proxy 在创建 meme chain 时，同时创建该 meme 的 state app 和 business app，并执行 append。

> **ABI 与 crate 结构约束**：遵循 `agents/context/project-rules.md` 中的 ABI 与 crate 拆分规则。meme 必须对齐 AMS / Blob-Gateway：
> - `abi/src/<family>.rs` 只做 re-export，operation enum 定义在 `abi/src/<family>/abi.rs`。
> - business app 和 state app 拆分为 `<family>/app/` 和 `<family>/state/` 两个 crate，分别命名为 `<family>-app` 和 `<family>-state`。
> - 这是为了避免 `linera bcs-serialize-application-operation` 遇到 `self::` re-export 时报 `unexpected token`（blob-gateway 已踩过这个坑）。

## 2. 目录结构变更

```
abi/src/meme.rs              # 改为纯 re-export 模块（同 ams.rs）
abi/src/meme/abi.rs          # 新增：从 abi/src/meme.rs 迁过来的 business app ABI
abi/src/meme/state_v1.rs     # 新增：state app 的 ABI

meme/app/Cargo.toml          # 新增：原 meme crate 拆成 meme-app
meme/app/src/                # 新增：business app
meme/state/Cargo.toml        # 新增：state app crate
meme/state/src/              # 新增：state app v1
meme/state/tests/            # 新增

proxy/src/                   # 修改 CreateMeme / CreateMemeExt 流程

tools/deploy/src/linest/     # 增加 meme-state bytecode 编译和 proxy 参数
scripts/run_local.sh         # 增加 meme-state 编译和 proxy 参数
```

根目录 `Cargo.toml` workspace 同步调整：
- `members` 中 `"meme"` 替换为 `"meme/app"`、`"meme/state"`。
- `[workspace.dependencies]` 中 `meme = { path = "./meme" }` 替换为 `meme-app = { path = "./meme/app" }`、`meme-state = { path = "./meme/state" }`。

## 3. ABI 变更

### 3.1 `abi/src/meme.rs`（改为 re-export 模块）

参考 `abi/src/ams.rs`：

```rust
pub mod abi;
pub mod state_v1;

pub use self::abi::{
    InstantiationArgument as MemeInstantiationArgument, Liquidity, Meme, MemeAbi,
    MemeMessage, MemeOperation, MemeParameters, MemeResponse, Metadata, MiningBase,
    MiningInfo, TransferFromApplicationReceipt, TransferFromApplicationReceiptPayload,
    TransferFromApplicationReceiptPurpose,
};

pub use self::state_v1::{
    MemeStateAbi, MemeStateV1Operation, MemeStateV1Response, StateInstantiationArgument,
};
```

### 3.2 新增 `abi/src/meme/abi.rs`

把当前 `abi/src/meme.rs` 里的 `Meme`、`MemeOperation`、`MemeMessage`、`MemeParameters`、`InstantiationArgument` 等全部迁到 `abi/src/meme/abi.rs`。

`MemeOperation` 增加 state 管理操作：

```rust
pub enum MemeOperation {
    // ... 原有业务操作

    AppendState {
        state_application_id: ApplicationId,
    },
    AppendStates {
        state_application_ids: Vec<ApplicationId>, // 批量 append，用于 proxy 创建新 meme
    },
    Handoff {
        new_business_application_id: ApplicationId,
    },
}
```

- `AppendState`：与 AMS / Blob-Gateway 保持一致，单条 append，linest 升级时可用。
- `AppendStates`：批量 append，proxy 创建新 meme 时使用，减少跨 app 调用次数。

`MemeInstantiationArgument`（即 `InstantiationArgument`）**不填 state app id**，因为 state app 在 business app 创建后通过 `AppendState` 逐个写入：

```rust
pub struct InstantiationArgument {
    pub meme: Meme,
    pub blob_gateway_application_id: Option<ApplicationId>,
    pub ams_application_id: Option<ApplicationId>,
    pub proxy_application_id: Option<ApplicationId>,
    pub swap_application_id: Option<ApplicationId>,
}
```

### 3.3 新增 `abi/src/meme/state_v1.rs`

```rust
use async_graphql::{Request, Response};
use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::{Account, ApplicationId, ContractAbi, ServiceAbi},
};
use serde::{Deserialize, Serialize};

pub struct MemeStateAbi;

impl ContractAbi for MemeStateAbi {
    type Operation = MemeStateV1Operation;
    type Response = MemeStateV1Response;
}

impl ServiceAbi for MemeStateAbi {
    type Query = Request;
    type QueryResponse = Response;
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct StateInstantiationArgument {
    pub business_application_id: ApplicationId,
    pub operator: Option<Account>,
}

#[derive(Debug, Clone, Deserialize, Eq, PartialEq, Serialize, GraphQLMutationRoot)]
pub enum MemeStateV1Operation {
    // 把原来 MemeOperation 里涉及状态的操作搬过来
    Transfer { to: Account, amount: Amount },
    TransferFrom { from: Account, to: Account, amount: Amount },
    TransferFromApplication { to: Account, amount: Amount },
    Approve { spender: Account, amount: Amount },
    Mint { to: Account, amount: Amount },
    Redeem { amount: Option<Amount> },
    Mine { nonce: CryptoHash },
    // ... 根据实际需要从 MemeOperation 拆分
}

#[derive(Debug, Clone, Deserialize, Eq, PartialEq, Serialize)]
pub enum MemeStateV1Response {
    Ok,
    Fail(String),
    Balance(Amount),
    Allowance(Amount),
    // ...
}
```

> **注意**：这里需要进一步梳理哪些 operation 应该进 state app，哪些留在 business app。原则是：business app 负责路由和权限校验，state app 负责存储。

## 4. Meme Business App 改造（`meme/app`）

原 `meme` crate 迁到 `meme/app`，package 名改为 `meme-app`，`Cargo.toml` 里的 `[[bin]]` 改为 `meme_app_contract` / `meme_app_service`。

### 4.1 `meme/app/src/state.rs`（瘦身）

```rust
pub struct MemeState {
    pub state_applications: MapView<u16, ApplicationId>,
    pub latest_state_version: RegisterView<u16>,
}
```

### 4.2 `meme/app/src/state/adapter/contract.rs`

实现 `PublicStateBaseInterface`。`AppendState` 的 handler 层使用 `only_application_creator()` 校验权限，与 AMS / Blob-Gateway 一致：

```rust
impl<R: ContractRuntimeContext> PublicStateBaseInterface for ContractStateAdapter<R> {
    type Error = StateError;

    async fn append_state(
        &mut self,
        state_application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        self.state.borrow_mut().append_state(state_application_id).await
    }

    async fn append_states(
        &mut self,
        state_application_ids: Vec<ApplicationId>,
    ) -> Result<(), Self::Error> {
        self.state.borrow_mut().append_states(state_application_ids).await
    }

    async fn handoff(&mut self, new_business_application_id: ApplicationId) -> Result<(), Self::Error> {
        // 调用当前 state app 执行 handoff
    }

    async fn set_operator(&mut self, _new_operator: Account) -> Result<(), Self::Error> {
        Err(StateError::OperatorNotSupported)
    }
}
```

对应 operation handler：

```rust
// AppendState
async fn handle(&mut self) -> Result<...> {
    self.runtime.borrow_mut().only_application_creator()
        .map_err(|e| HandlerError::RuntimeError(e.into()))?;
    self.state.append_state(self.state_application_id).await?;
    Ok(...)
}

// AppendStates
async fn handle(&mut self) -> Result<...> {
    self.runtime.borrow_mut().only_application_creator()
        .map_err(|e| HandlerError::RuntimeError(e.into()))?;
    self.state.append_states(self.state_application_ids.clone()).await?;
    Ok(...)
}
```

`append_states` 实现逻辑：

```rust
async fn append_states(
    &mut self,
    state_application_ids: Vec<ApplicationId>,
) -> Result<(), StateError> {
    let mut next_version = self.latest_state_version.get() + 1;
    for app_id in state_application_ids {
        if self.state_applications.contains_key(&next_version).await? {
            return Err(StateError::AlreadyExists);
        }
        self.state_applications.insert(&next_version, app_id)?;
        next_version += 1;
    }
    self.latest_state_version.set(next_version - 1);
    Ok(())
}
```

### 4.3 `meme/app/src/contract_inner/handlers/operation/*.rs`

Business app 需要根据 operation 类型路由到对应 state version。例如 `transfer.rs`：

```rust
async fn handle(&mut self) -> ... {
    self.runtime.borrow_mut().only_application_creator()?; // 或其他权限
    // Transfer 路由到 v1 state app
    let state_app_id = self.state.state_application(1).await?;
    let response = self.runtime.borrow_mut().call_application(
        state_app_id.with_abi::<MemeStateAbi>(),
        &MemeStateV1Operation::Transfer { to, amount },
    );
    match response {
        MemeStateV1Response::Ok => Ok(...),
        MemeStateV1Response::Fail(err) => Err(...),
        _ => Err(...),
    }
}
```

### 4.4 `meme/app/src/service.rs`

查询类接口（balance、allowance、mining_info）通过 `call_application` 转发到对应 state version。

### 4.5 多 state version 路由与聚合

每个 state version 负责一类状态。Business app 按 append 顺序给本地 version 编号（1, 2, 3...），并根据本地 version 路由 operation：

```rust
// Proxy 按全局 version 顺序 append，本地 version 自动对齐
// 全局 v1 -> 本地 1，全局 v2 -> 本地 2，全局 v3 -> 本地 3

// 写操作：直接路由到对应本地 version
Transfer { ... }         -> state_applications[1] (v1 balances)
UpdateMiningInfo { ... }  -> state_applications[2] (v2 mining)
AddLiquidity { ... }     -> state_applications[3] (v3 liquidity)

// 读操作：可能需要聚合多个 version
GetUserInfo(account) -> {
    balance: query state_applications[1],
    mining_info: query state_applications[2],
    liquidity: query state_applications[3],
}
```

新增 version 时（例如 v4），business app 的 handler 需要增加对 `state_applications[latest_state_version]` 的访问。旧 meme 如果没有 v4，则缺少对应功能，但其他功能继续正常。

> 约束：state version 必须连续注册，不能跳过。如果跳过某个 version，本地编号和全局 version 会错位。

## 5. Meme State App（新增 `meme/state`）

### 5.1 `meme/state/Cargo.toml`

参考 `blob-gateway/state/Cargo.toml` 和 `ams/state/Cargo.toml`。

### 5.2 `meme/state/src/state.rs`

每个 version 独立一个 crate，例如 `meme/state` 是 v1。后续 `meme/state-v2`、`meme/state-v3` 等分别负责新增状态。

从现有 `meme/src/state.rs` 搬过来 v1 字段：

```rust
pub struct MemeStateV1 {
    pub business_application_id: RegisterView<Option<ApplicationId>>,
    pub operator: RegisterView<Option<Account>>,

    pub initial_owner_balance: RegisterView<Amount>,
    pub owner: RegisterView<Option<Account>>,
    pub holder: RegisterView<Option<Account>>,

    pub meme: RegisterView<Option<Meme>>,
    pub initial_liquidity: RegisterView<Option<Liquidity>>,

    pub balances: MapView<Account, Amount>,
    pub allowances: MapView<Account, HashMap<Account, Amount>>,

    pub mining_info: RegisterView<Option<MiningInfo>>,
}
```

### 5.3 `meme/state/src/contract_inner/handlers/operation/*.rs`

实现 `MemeStateV1Operation` 的各个 handler，例如 `transfer.rs`：

```rust
async fn handle(&mut self) -> ... {
    self.runtime.borrow_mut().only_caller_creator()?;
    // 修改 balances
}
```

## 6. Proxy 改造

### 6.1 设计要点

- Proxy 维护所有 state app bytecode 的 registry（`version -> ModuleId`）。
- **新 meme 创建时，必须一次性完成**：创建 business app、创建所有已注册版本的 state app、把所有 state app id append 到 business app。整个流程在一个 message handler 内完成，保证原子性。
- 不同 version 的 state 是 append 关系，business app 需要所有 version 的 state 一起才能正常工作。
- Proxy 提供 service query，让 linest 能获取所有已创建的 child meme applications。
- Proxy 支持全局暂停/恢复（maintenance mode），升级期间 linest 先 pause，批量升级完再 resume。Pause 期间禁止新的 meme 创建。
- 已创建 meme 的升级由 linest 负责，不经过 proxy 合约触发。升级方式与 AMS / Blob-Gateway 一致（部署新 business app / append state apps / handoff）。
- 系统内可以同时存在多个 state version：旧 meme 只有 v1/v2，新 meme 直接创建 v1/v2/v3。

### 6.2 `abi/src/proxy.rs`

新增/修改字段：

```rust
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct ProxyInstantiationArgument {
    pub meme_bytecode_id: ModuleId,
    pub meme_state_bytecode_id: ModuleId, // 新增：v1 state bytecode
    pub operators: Vec<Account>,
    pub swap_application_id: ApplicationId,
}

#[derive(Debug, Deserialize, Serialize, Clone, SimpleObject)]
#[serde(rename_all = "camelCase")]
pub struct Chain {
    pub chain_id: ChainId,
    pub created_at: Timestamp,
    pub token: Option<ApplicationId>,
    // Proxy 不管理 state 升级，因此 Chain 不记录 state_tokens；需要时直接查询 meme business app。
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub enum ProxyMessage {
    // ...
    CreateMemeExt {
        business_bytecode_id: ModuleId,      // 改名：原 bytecode_id，明确是 business app
        state_bytecode_ids: BTreeMap<u16, ModuleId>, // 新增：所有已注册 state version 的 bytecode
        instantiation_argument: MemeInstantiationArgument,
        parameters: MemeParameters,
    },
    MemeCreated {
        chain_id: ChainId,
        token: ApplicationId,
        state_tokens: BTreeMap<u16, ApplicationId>, // 新增：version -> state app id，proxy 可记录日志
    },
    // ...
}

#[derive(Debug, Deserialize, Serialize, GraphQLMutationRoot)]
pub enum ProxyOperation {
    // ...
    RegisterMemeStateBytecode {
        version: u16,
        bytecode_id: ModuleId,
    },
    SetPaused {
        paused: bool,
    },
    UpdateMemeToken {
        chain_id: ChainId,
        new_token: ApplicationId,
    },
}
```

### 6.3 `proxy/src/state.rs`

新增 state bytecode registry 和创建开关：

```rust
pub struct ProxyState {
    pub meme_bytecode_id: RegisterView<Option<ModuleId>>,
    pub meme_state_bytecode_ids: MapView<u16, ModuleId>, // 新增：version -> bytecode
    pub latest_meme_state_version: RegisterView<u16>,    // 新增
    pub paused: RegisterView<bool>,                      // 新增：maintenance mode，pause 期间禁止新业务
    // ... existing fields
}
```

Proxy 初始化时：

```rust
self.meme_state_bytecode_ids.insert(&1, argument.meme_state_bytecode_id)?;
self.latest_meme_state_version.set(1);
self.paused.set(false);
```

`proxy/src/interfaces/state.rs` 新增方法：

```rust
async fn meme_state_bytecode_ids(&self) -> Result<BTreeMap<u16, ModuleId>, Self::Error>;
fn paused(&self) -> bool;
async fn set_paused(&mut self, paused: bool) -> Result<(), Self::Error>;
async fn update_meme_token(
    &mut self,
    chain_id: ChainId,
    new_token: ApplicationId,
) -> Result<(), Self::Error>;
```

`create_chain_token` 保持不变，只记录 business app token。

### 6.4 `proxy/src/contract_inner/handlers/message/create_meme.rs`

`CreateMemeHandler` 负责读取所有已注册 state bytecodes，一起发送到 meme chain。

```rust
async fn on_creation_chain_msg_create_meme(
    &mut self,
    instantiation_argument: MemeInstantiationArgument,
    parameters: MemeParameters,
) -> Result<HandlerOutcome<ProxyMessage, ProxyResponse>, HandlerError> {
    if self.state.paused() {
        return Err(HandlerError::ProxyPaused);
    }

    let chain_id = self.create_meme_chain().await?;
    self.fund_meme_chain_initial_liquidity(chain_id, parameters.clone());

    let business_bytecode_id = self.state.meme_bytecode_id();
    let state_bytecode_ids = self.state.meme_state_bytecode_ids().await?;

    let destination = chain_id;
    let mut outcome = HandlerOutcome::new();
    outcome.with_message(
        destination,
        ProxyMessage::CreateMemeExt {
            business_bytecode_id,
            state_bytecode_ids,
            instantiation_argument,
            parameters,
        },
        false,
    );

    self.state
        .create_chain(chain_id, self.runtime.borrow_mut().system_time())
        .map_err(Into::into)?;

    Ok(outcome)
}
```

### 6.5 `proxy/src/contract_inner/handlers/message/create_meme_ext.rs`

`CreateMemeExtHandler` 在 meme chain 上先创建 business app，然后按 version 顺序创建所有 state app，并逐个 append 到 business app。

```rust
fn create_meme_application(
    &mut self,
    bytecode_id: ModuleId,
    instantiation_argument: MemeInstantiationArgument,
    parameters: MemeParameters,
) -> ApplicationId {
    self.runtime
        .borrow_mut()
        .create_application::<MemeAbi, MemeParameters, MemeInstantiationArgument>(
            bytecode_id,
            &parameters,
            &instantiation_argument,
        )
        .forget_abi()
}

fn create_state_application(
    &mut self,
    state_bytecode_id: ModuleId,
    business_application_id: ApplicationId,
) -> ApplicationId {
    let argument = StateInstantiationArgument {
        business_application_id,
        operator: None,
    };
    self.runtime
        .borrow_mut()
        .create_application::<MemeStateAbi, (), StateInstantiationArgument>(
            state_bytecode_id,
            &(),
            &argument,
        )
        .forget_abi()
}

fn append_states_to_business_app(
    &mut self,
    business_application_id: ApplicationId,
    state_application_ids: Vec<ApplicationId>,
) {
    // 当前在 meme chain 上的 proxy app 上下文中
    // 直接调用同 chain 上的 meme business app，批量执行 AppendStates operation
    self.runtime
        .borrow_mut()
        .call_application::<MemeAbi>(
            business_application_id.with_abi::<MemeAbi>(),
            &MemeOperation::AppendStates {
                state_application_ids,
            },
        )
        .expect("Failed to append states to meme business app");
}

fn on_meme_chain_msg_create_meme(
    &mut self,
    business_bytecode_id: ModuleId,
    state_bytecode_ids: BTreeMap<u16, ModuleId>,
    instantiation_argument: MemeInstantiationArgument,
    parameters: MemeParameters,
) -> HandlerOutcome<ProxyMessage, ProxyResponse> {
    // 1. 创建 business app，state id 暂时为 None
    let business_application_id = self.create_meme_application(
        business_bytecode_id,
        instantiation_argument,
        parameters,
    );

    // 2. 设置 meme chain 权限
    let permissions = ApplicationPermissions {
        execute_operations: Some(vec![business_application_id]),
        mandatory_applications: vec![],
        close_chain: vec![business_application_id],
        change_application_permissions: vec![business_application_id],
        call_service_as_oracle: Some(vec![business_application_id]),
        make_http_requests: Some(vec![business_application_id]),
    };
    self.runtime
        .borrow_mut()
        .change_application_permissions(permissions)
        .expect("Failed change application permissions");

    // 3. 按 version 顺序创建所有 state app，最后批量 append 到 business app
    //    - 当前执行位置：meme chain 上的 proxy app contract
    //    - 被调用的 app：刚创建的 meme business app（也在 meme chain 上）
    //    - 调用方式：proxy app 通过 call_application 直接同步调用 AppendStates
    //    - business app 内部按 append 顺序分配本地 version 1, 2, 3...
    let mut state_application_ids = Vec::new();
    let mut state_tokens = BTreeMap::new();

    for (version, state_bytecode_id) in state_bytecode_ids {
        // 3.1 在 meme chain 上创建 vN state app
        let state_application_id = self.create_state_application(
            state_bytecode_id,
            business_application_id,
        );
        state_application_ids.push(state_application_id);
        state_tokens.insert(version, state_application_id);
    }

    // 3.2 在 meme chain 上，proxy app 调用 meme business app 的 AppendStates
    //     一次性把所有 state app ids 写入 business app.state_applications
    self.append_states_to_business_app(
        business_application_id,
        state_application_ids,
    );

    // 4. 回发 MemeCreated
    let meme_chain_id = self.runtime.borrow_mut().chain_id();
    let destination = self.runtime.borrow_mut().application_creator_chain_id();
    let mut outcome = HandlerOutcome::new();
    outcome.with_message(
        destination,
        ProxyMessage::MemeCreated {
            chain_id: meme_chain_id,
            token: business_application_id,
            state_tokens,
        },
        false,
    );
    outcome
}
```

说明：
- `MemeInstantiationArgument.state_application_id` 在创建时传 `None`，创建后通过 `AppendStates` 批量写入。
- `MemeOperation::AppendState` 与 AMS / Blob-Gateway 保持一致（单条 append），linest 升级时可用。
- `MemeOperation::AppendStates` 是 meme 特有的批量 append，proxy 创建新 meme 时使用，把所有 state app id 一次写入 business app。
- **调用链详细说明**：
  - 执行位置：meme chain 上的 proxy app contract（`CreateMemeExtHandler`）。
  - proxy app 先循环创建所有 state app，收集 ids。
  - 然后调用一次 `call_application::<MemeAbi>(business_app_id, MemeOperation::AppendStates { state_application_ids })`。
  - `call_application` 在**同一条 meme chain**上同步调用 meme business app 的 `execute_operation`。
  - 被调用的 meme business app 用 `only_application_creator()` 校验：当前 chain 正是它的 creator chain，因此通过。
  - business app 按顺序把 ids 写入 `state_applications`，本地 version 自动递增。
- Proxy 必须按全局 version 升序创建 state app，确保 business app 的本地 version 1, 2, 3... 与全局 version 对齐。
- 整个 `CreateMemeExtHandler` 是原子的：business app 创建、所有 state app 创建、`AppendStates` 调用，要么全部成功，要么全部 revert。

### 6.6 `proxy/src/contract_inner/handlers/message/meme_created.rs`

只更新 `Chain.token`，不记录 state tokens。

```rust
self.state
    .create_chain_token(self.chain_id, self.token)
    .await
    .map_err(Into::into)?;
```

`state_tokens` 仅用于日志或事件，proxy 不持久化。

### 6.7 Proxy Service API（供 linest 使用）

`proxy/src/service.rs` 新增 query 和 mutation：

```rust
#[Object]
impl QueryRoot {
    // 已有 query，linest 用来发现 child meme
    async fn meme_applications(&self) -> Vec<Chain> {
        // 返回所有已创建 meme 的 chain_id + business app id
    }

    async fn meme_state_bytecodes(&self) -> Vec<(u16, ModuleId)> {
        // 返回 proxy 注册的所有 state bytecodes
    }

    async fn paused(&self) -> bool {
        *self.state.paused.get()
    }
}

#[Object]
impl MutationRoot {
    async fn set_paused(&self, paused: bool) -> [u8; 0] {
        self.runtime.schedule_operation(
            &ProxyOperation::SetPaused { paused }
        );
        []
    }

    async fn update_meme_token(
        &self,
        chain_id: ChainId,
        new_token: ApplicationId,
    ) -> [u8; 0] {
        self.runtime.schedule_operation(
            &ProxyOperation::UpdateMemeToken { chain_id, new_token }
        );
        []
    }
}
```

权限：`setPaused` 和 `updateMemeToken` 只能由 proxy operator 调用（handler 里校验 `validate_operator`）。

## 7. Linest / 部署改造

### 7.1 `tools/deploy/src/linest/models/app_family.py`

`meme` 家族的部署需要增加 state app 步骤。和 blob-gateway 类似，但部署流程由 proxy 内部完成时，linest 可能只需要编译 bytecode 并传给 proxy。

### 7.2 `scripts/run_local.sh`

- 编译 `meme/app` 和 `meme/state` wasm：
  ```bash
  cargo build --release --target wasm32-unknown-unknown -p meme-app
  cargo build --release --target wasm32-unknown-unknown -p meme-state
  ```
- publish bytecode（产物名跟随 `[[bin]]`）：
  ```bash
  MEME_APP_MODULE_ID=$(publish_bytecode meme-app)
  MEME_STATE_MODULE_ID=$(publish_bytecode meme-state)
  ```
- proxy 的 `InstantiationArgument` 需要传入 `meme_bytecode_id`（对应 `meme-app`）和 `meme_state_bytecode_id`。

### 7.3 Proxy 初始化

创建 proxy app 时，需要把 `meme_state_bytecode_id` 作为 instantiation argument 传入：

```rust
let proxy_argument = ProxyInstantiationArgument {
    meme_bytecode_id: MEME_APP_MODULE_ID,
    meme_state_bytecode_id: MEME_STATE_MODULE_ID, // 新增
    operators: ...,
    swap_application_id: SWAP_APPLICATION_ID,
};
```

## 8. 升级流程

### 8.1 Proxy 注册新版本 bytecode

当发布新的 meme-state bytecode 后，需要先注册到 proxy，这样之后新创建的 meme 才能使用最新版本。

增加 `ProxyOperation::RegisterMemeStateBytecode`：

```rust
pub enum ProxyOperation {
    // ...
    RegisterMemeStateBytecode {
        version: u16,
        bytecode_id: ModuleId,
    },
}
```

处理逻辑：

```rust
async fn register_meme_state_bytecode(
    &mut self,
    version: u16,
    bytecode_id: ModuleId,
) -> Result<(), ProxyError> {
    if version == 0 || version <= *self.latest_meme_state_version.get() {
        return Err(ProxyError::InvalidStateVersion);
    }
    self.meme_state_bytecode_ids.insert(&version, bytecode_id)?;
    self.latest_meme_state_version.set(version);
    Ok(())
}
```

### 8.2 已创建 meme 的升级流程（linest 批量升级）

Proxy 不触发升级，只提供**发现机制**和**暂停开关**。升级由 linest 批量执行。

**升级前准备**

1. Linest publish 新的 `meme-state-vN` bytecode。
2. Linest 调用 `ProxyOperation::RegisterMemeStateBytecode { version: N, bytecode_id }`，把 bytecode 注册到 proxy registry。

**linest 批量升级步骤**

1. **Pause proxy**
   - Linest 调用 proxy service mutation `setPaused(true)`。
   - 之后 `CreateMeme` operation 会被拒绝，避免升级期间产生新的 child meme。

2. **发现所有 child meme**
   - Linest 查询 proxy service `memeApplications()`，拿到所有 meme 的 `(chain_id, business_app_id)`。

3. **批量升级每个 meme**

   对每个 meme，linest 执行一个标准 upgrade plan（与 AMS / Blob-Gateway 一致）：

   a. 查询 meme business app 当前有哪些 state apps（service query `stateApplications`）。
   b. 部署新的 meme business app v2（必须换新 business app，因为旧 business app 不认识新的 state version）。
   c. 部署新的 vN state app。
   d. 通过 `MemeOperation::AppendStates` 一次性把所有 state apps（旧 + 新）append 到 v2。
   e. 对旧 business app v1 执行 `Handoff { new_business_application_id: v2_id }`。
   f. 更新 proxy 的 `Chain.token` 为 v2_id（通过 proxy mutation `updateMemeToken`）。

4. **Resume proxy**
   - 所有 meme 升级完成后，linest 调用 `setPaused(false)`。

**关键设计**

- 升级期间 proxy 被 pause，新 meme 创建阻塞，保证一致性。
- Linest 通过 proxy service 发现 child applications，不需要自己维护列表。
- 每个 meme 的 upgrade plan 复用现有 AMS / Blob-Gateway 的 `AppendStateStep` / `HandoffStep` 逻辑。
- Proxy 的 `Chain.token` 需要在 handoff 后同步更新，否则 proxy 查询会返回旧 business app。

### 8.3 多版本共存

- Proxy registry 记录所有已注册 state bytecodes。
- 新 meme 创建时一次性部署 v1..vN 所有 state app。
- 已存在 meme 由 linest 批量升级，可以停留在旧版本或追加新版本。
- 不同 meme 之间的 state version 组合相互隔离。

## 9. 已确认结论

1. **MemeOperation 路由到 state version 的方式**：
   - 不在 business app 里维护 operation -> version 的映射表。
   - 路由逻辑写死在 **state adapter 层**：adapter 根据当前 operation 类型，自行决定调用哪个 state version 的 API。
   - 例如 `Transfer` / `Balance` 等基础资产操作固定路由到 v1 state app；v2 新增的状态操作在 adapter 中扩展为调用 v2 state app。

2. **Proxy operator 级 operation 的调用权限**：
   - `RegisterMemeStateBytecode`、`SetPaused`、`UpdateMemeToken` 仅允许 proxy operator 调用。
   - 不引入 `RequiredApplicationIds` 或多签治理，保持与当前 AMS / Blob-Gateway 的 operator 模式一致。

3. **新增 state version 时的扩展方式**：
   - 必须采用 **adapter 模式**，不能硬编码。
   - 当前 adapter 只对接 v1 state app；后续新增 v2 state app 时，在 adapter 中增加 v2 state API 的访问路径。
   - Business app handler 保持简洁，只通过 adapter 调用抽象接口，不关心底层是 v1 还是 v2。

## 10. 下一步建议

1. 从 `abi/src/meme/state_v1.rs` 开始实现。
2. 新增 `meme/state` crate，把现有 `meme/src/state.rs` 的字段搬过去。
3. 新增 `meme/app` crate，把现有 `meme/src` 改造为 business app 形态。
4. 改造 proxy：CreateMeme / CreateMemeExt 流程、state bytecode registry、pause/query API。
5. 更新 linest：支持从 proxy 发现 child meme 并批量升级。
