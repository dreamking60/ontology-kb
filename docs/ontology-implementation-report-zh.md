# 银行业本体应用实现与复现报告

> 项目：Banking Concept Knowledge Base（MVP）  
> 报告目标：说明本仓库如何搭建银行业务本体、如何运行与验证，并结合企业级产品的公开实践给出可演进方案。  
> 口径：本报告以仓库当前实现和报告撰写时可访问的官方文档为准；厂商能力均区分“官方事实”和“本文分析”。

## 1. 执行摘要

本项目已实现一个可离线运行的银行业务/产品概念知识库：以 OWL2/Turtle 描述概念模型，以 RDF 个体描述示例数据，使用 `rdflib` 装载、`owlrl` 执行 OWL2-RL 推理、FastAPI 提供查询接口，并在其上增加检索、RAG 和只读工具调用 Agent。

当前实测基线：

- 3 个权威 Turtle 文件；
- 842 个 RDF 三元组；
- 60 个类、34 个示例个体；
- 2 个对象属性、7 个数据属性、1 个 FIBO 对齐注释属性；
- 13 个 FIBO 注释映射；
- 98 项 pytest 测试全部通过；
- 7 个 OpenSpec 规范严格校验通过；
- HermiT 未发现不可满足类。

项目最值得复现的设计不是“把资料塞进图数据库”，而是将知识分为：

1. **TBox（概念模式）**：类、层级、属性及其定义；
2. **ABox（事实数据）**：具体产品、账户、主体及属性值；
3. **Alignment（外部标准对齐）**：本地概念到 FIBO 的可验证注释；
4. **Reasoning（推理）**：标准 OWL entailment 与业务规则分层；
5. **Application（应用）**：搜索、浏览、问答、Agent 工具；
6. **Governance（治理）**：来源、测试、版本、审批和安全边界。

但它仍是单机只读 MVP，而不是 Palantir 意义上的“操作型本体”：目前没有真实数据绑定、实体解析、持久图存储、生产权限、版本审批运行时，以及可写回业务系统的 Action。

---

## 2. 什么是这里的“本体”

这里的本体不是哲学本体论，而是业务语义模型。它回答六类问题：

| 问题 | 本体构件 | 本项目示例 |
|---|---|---|
| 业务中有哪些东西？ | Class / 类型 | 产品、存款、账户、客户 |
| 哪些是上下位概念？ | `rdfs:subClassOf` | 大额存单 → 定期存款 → 存款 → 产品 |
| 每类东西有哪些事实？ | Datatype Property | 期限、最低金额、利率、风险等级 |
| 东西之间如何关联？ | Object Property | 产品由主体提供、账户支持产品 |
| 具体对象是什么？ | Individual / 实例 | 示例大额存单、示例商业银行 |
| 能推出什么新事实？ | OWL/规则 | 大额存单实例也是存款和产品实例 |

本体的价值在于把散落在表名、字段名、文档和人员经验中的业务含义提升为可复用、可验证、可查询的契约。LLM 只是本体的消费者之一，不应成为事实来源。

---

## 3. 当前系统架构

```text
ontology/banking-core.ttl       TBox：类、层级、属性
ontology/seed-corpora.ttl       ABox：公开通用示例个体
ontology/fibo-alignment.ttl      Alignment：到 FIBO 的注释映射
              │
              ▼
       rdflib 只读内存图
        ├─ 标签/同义词搜索与层级浏览
        ├─ SPARQL SELECT / ASK
        ├─ owlrl OWL2-RL 推理副本
        └─ Python 声明式演示规则
              │
              ▼
          FastAPI API
        ├─ 概念、树、详情、推理
        ├─ RAG + 引用
        └─ 只读工具 Agent + SSE
              │
              ▼
       原生 HTML/CSS/JS 单页应用
```

关键源码：

- 图装载及本体访问：`src/banking_kb/kb.py`
- 检索：`src/banking_kb/search.py`、`src/banking_kb/rag.py`
- 推理与规则：`src/banking_kb/reasoning.py`、`src/banking_kb/rules.py`
- Agent 工具：`src/banking_kb/tools.py`、`src/banking_kb/agent.py`
- API：`src/banking_kb/api.py`
- Web UI：`ui/static/`

技术选型适合复现和教学：Python 依赖少、Turtle 可直接在 Protégé 编辑、不要求独立数据库或 Java 服务。代价是数据每次启动全量装入内存，不适合大规模和高并发生产环境。

---

## 4. 本体如何从零搭建（核心）

### 4.1 第一步：先定义业务问题，而不是先画“大而全”的图

建议先写 10—20 个 competency questions（能力问题），例如：

1. 大额存单是否属于存款？
2. 定期存款有哪些子类？
3. 哪些示例产品受存款保险保障？
4. 哪些产品由某银行提供？
5. 期限不少于 60 个月的定期存款应归入什么演示分类？

每个问题都要能落到一条预期查询或测试。无法支持任何业务问题的概念先不建。企业产品最新趋势也是“问题驱动”：Stardog 的 Voicebox 官方流程明确从项目用途和常见问题出发，再选择数据源、生成模型与映射，并由人工复核。[官方说明](https://docs.stardog.com/voicebox/guided-ontology-creation-and-mapping/)

### 4.2 第二步：划定边界与顶层概念

本项目选择三个应用入口根类：

```text
Product（产品）
├─ Deposit（存款）
│  ├─ DemandDeposit（活期存款）
│  └─ TimeDeposit（定期存款）
│     └─ CertificateOfDeposit（大额存单）
├─ Loan（贷款）
└─ WealthManagementProduct（理财产品）

Account（账户）
Party（主体）
```

扩展模型中另有 `Rate` 和 `BankingEvent`，但当前树接口只展示前三个根。这说明“本体中存在”与“应用已消费”是两个不同验收项。

边界原则：

- 类表示可复用的类型，不用类代替具体产品；
- 个体表示具体对象或样例；
- 同一分类轴保持一致。例如“按用途分类贷款”和“按担保方式分类贷款”是两个维度，不能未经设计就混在单继承树中；
- 不确定的概念先记录为待决项，避免制造错误等价关系。

### 4.3 第三步：确定稳定 IRI 与命名规范

本项目使用：

```turtle
@prefix bc: <https://ontology.example/banking-core#> .
@prefix ex: <https://ontology.example/seed#> .
```

复现时应把 `ontology.example` 替换成组织长期控制的域名，例如：

```text
https://data.examplebank.com/ontology/banking/core#
https://data.examplebank.com/resource/product/
```

建议规范：

- IRI 本地名使用稳定英文 PascalCase，如 `CertificateOfDeposit`；
- 展示名称使用语言标签，不把中文直接编码进 IRI；
- IRI 一经发布不因中文名称调整而变化；
- 废弃概念保留 IRI，增加 deprecated、replacement 和迁移说明；
- schema、instance、reference-data 使用不同命名空间。

### 4.4 第四步：建立 TBox——类、层级、定义

当前类的最小模板如下：

```turtle
bc:TimeDeposit a owl:Class ;
    rdfs:subClassOf bc:Deposit ;
    rdfs:label "定期存款"@zh, "Time Deposit"@en ;
    skos:altLabel "定存"@zh ;
    skos:definition "事先约定存期、到期支取本息的存款。"@zh ;
    skos:editorialNote "Public generic definition; not internal data."@en .
```

每个类至少应有：

- 唯一稳定 IRI；
- 中文和英文 `rdfs:label`；
- 可检索同义词 `skos:altLabel`；
- 无循环定义的 `skos:definition`；
- 直接父类；
- 来源或编辑说明；
- owner、status、version（生产化时新增）。

不要一开始大量使用复杂 OWL 限制。先确保层级、定义与实例边界被业务专家接受，再逐步加入 `owl:Restriction`、互斥类和等价类。当前项目为保证 OWL2-RL 可运行，模型有意偏轻量。

### 4.5 第五步：定义属性和关系

数据属性示例：

```turtle
bc:termMonths a owl:DatatypeProperty ;
    rdfs:domain bc:Product ;
    rdfs:range xsd:integer ;
    rdfs:label "期限（月）"@zh, "Term (months)"@en .
```

对象属性示例：

```turtle
bc:offeredBy a owl:ObjectProperty ;
    rdfs:domain bc:Product ;
    rdfs:range bc:Party ;
    rdfs:label "提供机构"@zh, "Offered by"@en .
```

生产建模时，每个属性还应明确：

- 数据类型、单位、精度、是否可空；
- domain/range；
- 单值或多值、基数；
- 是否为标识属性；
- 生效时间、记录时间；
- 数据来源、质量规则；
- 敏感等级和访问策略。

特别提醒：OWL 的 domain/range 主要用于语义推断，不等同于数据库约束。若需要阻止脏数据进入，应增加 SHACL 校验层。例如“期限必须是非负整数”“产品必须有中文标签”“提供机构最多一个”等更适合 SHACL。

### 4.6 第六步：建立 ABox——用“概念卡片”装载样例事实

```turtle
ex:DemoCertificateOfDeposit a bc:CertificateOfDeposit ;
    rdfs:label "示例大额存单"@zh, "Example certificate of deposit"@en ;
    skos:definition "演示用大额存单。"@zh ;
    skos:editorialNote "Public generic demo seed; not internal bank data."@en ;
    bc:termMonths 36 ;
    bc:minimumAmount 200000 ;
    bc:interestRate 2.6 ;
    bc:depositInsuranceCovered true ;
    bc:offeredBy ex:SampleBank .
```

TBox 与 ABox 分文件的好处是：

- 模型和业务数据可独立版本化；
- 推理结果不污染源模型；
- 可用同一模型加载不同环境的数据；
- 审批职责可分开：语义委员会管 schema，数据 owner 管 mapping/instance。

真实数据接入时，不建议人工生成全部个体。应增加声明式 mapping：表主键如何生成 IRI、列如何映射属性、外键如何生成关系、何时刷新。可采用 R2RML/SMS 类标准，或至少使用受版本控制的 YAML 映射契约。

### 4.7 第七步：对齐行业标准，但不要盲目整体导入

项目使用 `bc:alignedToFibo` 将本地类注释到固定版本的 FIBO IRI：

```turtle
bc:CertificateOfDeposit
    bc:alignedToFibo
      <https://spec.edmcouncil.org/fibo/.../TimeCertificateOfDepositAccount> .
```

策略是“对齐而不 `owl:imports`”：

- FIBO 只作术语锚点；
- 本地中文定义保持自主；
- 固定上游 commit；
- 脚本验证目标 IRI 确实存在；
- 对非一一对应的概念明确记录语义风险。

这比全量导入更适合 MVP。全量导入会带来大模型、依赖链、推理性能和升级风险。本项目还明确记录：FIBO 将很多“存款”建模为账户类型，因此本地产品类到 FIBO 账户类只是最近术语映射，不能声明 `owl:equivalentClass`。

### 4.8 第八步：将标准推理与业务规则分离

系统有三层事实来源：

1. `asserted`：源文件直接声明；
2. `inferred`：OWL2-RL 根据子类、类型等推导；
3. `rule-derived`：业务规则推导。

例如：

```text
已声明：示例大额存单 rdf:type 大额存单
本体：大额存单 subClassOf 定期存款 subClassOf 存款 subClassOf 产品
推理：示例大额存单也是定期存款、存款、产品
```

演示业务规则：

```text
IF 对象是定期存款或其子类实例
AND termMonths >= 60
THEN 对象属于“长期定期存款（演示分类）”
```

实现时先复制基础图，在副本上 materialize，再执行规则；不将推理结果写回权威 Turtle。这保证可重复计算，并可比较推理前后三元组数量。生产中每条规则还应有 owner、版本、适用日期、优先级、输入输出、解释模板和测试样例。

### 4.9 第九步：以业务问题驱动验证

至少建立五类自动测试：

- **语法**：全部 Turtle 可解析；
- **结构**：无悬空 IRI、类层级无环、关键类存在；
- **内容**：双语标签、定义、来源、类别覆盖；
- **语义**：预期 entailment 成立，非预期分类不成立；
- **应用**：搜索、API、RAG 引用、Agent 只读限制符合契约。

完整 DL 一致性由 HermiT 检查；OWL2-RL 运行成功只说明规则闭包可计算，不等价于完整逻辑一致性。生产化建议加入 SHACL：一致性检查回答“模型是否逻辑冲突”，SHACL 回答“数据是否符合业务录入要求”。

---

## 5. 完整复现步骤

### 5.1 环境

- Python 3.11+（当前虚拟环境为 Python 3.12）；
- 可选 Java，用于 HermiT；
- Linux/macOS 或支持 Make/Python 的环境。

### 5.2 安装、装载与验证

```bash
cd /home/dreamking/ontology
make setup
make load
make test
make check-alignment
make check-consistency
openspec validate --specs --strict
```

本次实际结果：

```text
Loaded 3 file(s): 842 triples, 60 classes, 34 individuals.
98 passed, 2 warnings
FIBO alignment: 13 annotations, all resolved
HermiT: No inconsistent classes detected
OpenSpec: 7 passed, 0 failed
```

两条 pytest warning 均为测试依赖弃用提示，不影响功能通过。

### 5.3 启动应用

```bash
make api
```

浏览器访问 `http://127.0.0.1:8000`，API 文档访问 `http://127.0.0.1:8000/docs`。

验证调用：

```bash
curl 'http://127.0.0.1:8000/api/concepts?q=定存'
curl 'http://127.0.0.1:8000/api/tree'
curl 'http://127.0.0.1:8000/api/concepts/CertificateOfDeposit'
curl -X POST 'http://127.0.0.1:8000/api/reasoning/demo' \
  -H 'content-type: application/json' -d '{}'
```

不配置 LLM 时，问答自动使用确定性摘要；配置 OpenAI-compatible endpoint 后可使用 RAG/Agent。银行环境使用外部模型前必须审查数据出域。

### 5.4 从零复制本体内容的推荐顺序

1. 复制目录结构，但不要复制示例命名空间；
2. 写 10—20 个能力问题和预期答案；
3. 选择 3—7 个核心对象类型；
4. 每类只建支撑问题所需的属性和关系；
5. 为每类写 2—3 个正例和反例个体；
6. 建立解析、SHACL、推理和查询测试；
7. 再接入真实表映射；
8. 最后接入 RAG/Agent，不要反过来让 LLM“猜”本体。

---

## 6. 企业最新公开实践对比

### 6.1 Palantir Foundry：从“知识可查”升级为“业务可执行”

**官方事实。** Palantir 的 Ontology 包含 Object type/instance、Property、Link type，并扩展到 Shared Property、Value Type、Interface、Object Set、Derived Property；Action Type 和 Function 将业务操作与计算纳入同一体系。官方文档同时提供对象/链接、动作、函数、场景、分支与 proposal review 等能力：[Ontology Core Concepts](https://www.palantir.com/docs/foundry/ontology/core-concepts/)、[Object and Link Types](https://www.palantir.com/docs/foundry/object-link-types/type-reference)、[Action Types](https://www.palantir.com/docs/foundry/action-types/overview/)、[Ontology Branching](https://www.palantir.com/docs/foundry/ontologies/branching-ontology/)。

典型路径可概括为：

```text
数据接入/转换
→ 定义对象、属性、主键和链接并绑定数据
→ 定义派生属性、接口
→ 定义 Action 的参数、前置规则、授权与副作用
→ 用 Function 计算或产生 ontology edits
→ 在 Workshop / Object Explorer / Vertex / OSDK / AIP 中消费
→ 分支、评审、发布、监控、回滚
```

**本文分析。** Palantir 的差异不在于是否使用 RDF/OWL，而在于把名词（对象）、关系（链接）、动词（Action）、计算（Function）和权限统一成运行时契约，即“操作型语义层”。本项目目前覆盖了名词、少量关系、查询与推理，但还缺少动作、写回、细粒度授权和变更运行时。

可复现的关键不是照搬产品界面，而是为本项目增加：

```text
Action = 参数 schema + 前置条件 + 授权 + 幂等键
       + 状态变更/外部调用 + 审计日志 + 补偿/撤销
```

例如“发起产品上架审核”应是一等动作，而不是 Agent 自由生成 SQL。

### 6.2 Stardog：开放标准、虚拟图和查询时推理

**官方事实。** Stardog Virtual Graph 通过声明式 mapping 把关系库、CSV、JSON/NoSQL 等映射为 RDF。SPARQL 会被改写成源端 SQL 等原生查询；本地图与远端图可联邦查询，也可选择物化。[Virtual Graphs](https://docs.stardog.com/virtual-graphs/)

Stardog 的推理采用 lazy/late-binding 的查询时改写，不把推理事实预先全部物化；schema 可由 RDFS/OWL axioms 与用户规则组成。[Inference Engine](https://docs.stardog.com/inference-engine/)

**本文分析。** 这对本项目最直接的启示是：从文件型 MVP 向生产升级时，不一定要复制全部银行数据。可以为实时或敏感数据建立虚拟映射，对低延迟、复杂推理数据再物化，并明确刷新 SLA。本项目当前“启动时全量加载到内存、按需在副本上推理”的方式只适合小数据集。

### 6.3 TopQuadrant / TopBraid EDG：OWL/SHACL 与治理工作流

**官方事实。** TopBraid 使用 RDFS/OWL 建类与属性，并大量使用 SHACL Node Shape/Property Shape 描述结构和约束；其预置模型还通过 Asset class 与 Aspect class 分离具体资产及可复用属性组。[TopBraid EDG Ontologies](https://www.topquadrant.com/blog/overview-of-topbraid-edg-ontologies)

**本文分析。** 本项目可借鉴两点：

1. 增加 SHACL，让标签、基数、类型、金额范围、引用完整性成为发布门禁；
2. 将“可识别、可追溯、可生效、可治理”等横切属性抽成可复用 aspect，而不是在每个类重复定义。

### 6.4 PoolParty / Graphwise：多语言词表与内容语义化

**官方事实。** PoolParty 产品路径以 SKOS/RDF/URI 为基础，围绕 Concept Scheme、Top Concept、Concept、多语言 preferred/alternative labels、broader/narrower/related 关系、Linked Data、Extractor 和 Recommender 建设语义资产；2025 R2 官方文档也展示了仓储、图结构、用户组、工作流与 API 等模块。[Graphwise Platform Architecture](https://help-dev.poolparty.biz/en/poolparty-overview/graphwise-platform-system-architecture.html)

**本文分析。** 若目标首先是中文术语治理、文档标注、企业搜索或 GraphRAG，PoolParty 路线比一开始追求复杂 OWL 更实际。本项目已经有中英标签和同义词，但缺少术语审批、同义词来源、歧义词、概念历史和文本抽取管道。

### 6.5 Microsoft Fabric Ontology：Lakehouse 原生业务语义层

**官方事实。** Microsoft Fabric 的 Ontology（Preview）把企业语义表示为 entity type、entity instance、property、relationship，并把定义绑定到 OneLake 数据源；其图支持来源 lineage、图分析、规则推断和面向业务术语的查询，还提供自然语言到 ontology query 的说明。该功能明确标为 Preview。[Microsoft Fabric Ontology Overview](https://learn.microsoft.com/en-gb/fabric/iq/ontology/overview)

**本文分析。** Fabric 表明云数据平台正在把“表之上的业务对象层”产品化。其对本项目的启示是：schema 只是第一步，必须把 entity identity、数据绑定、关系键、来源 lineage、刷新机制和查询路由作为本体平台的一部分。

### 6.6 横向定位

| 产品/路线 | 最强项 | 对本项目的启示 |
|---|---|---|
| Palantir | 对象+链接+Action+Function+权限的执行闭环 | 补齐动作和写回，而非只做问答 |
| Stardog | RDF/OWL/SPARQL、虚拟图、查询时推理 | 补齐声明式数据映射与联邦查询 |
| TopQuadrant | OWL/SHACL 策展、语义资产治理 | 补齐约束、审批、版本发布 |
| PoolParty | SKOS、多语言术语、内容标注 | 补齐中文术语生命周期与文档抽取 |
| Microsoft Fabric | OneLake 数据绑定、图与 AI 共享语义 | 补齐身份、lineage、刷新和跨域绑定 |

结论：这些方案不是完全同类。Palantir 更偏操作型语义层；Stardog 更偏标准知识图与推理；TopQuadrant/PoolParty 更偏语义资产治理；Fabric 更偏云数据平台原生语义绑定。选型应由闭环场景决定，而不是由“本体”这一名称决定。

---

## 7. 当前实现的优点与不足

### 7.1 已做对的部分

- TBox、ABox、外部 alignment 分层清晰；
- Turtle 是权威源，Protégé 兼容；
- FIBO 固定版本且映射可离线验证；
- 推理在副本上运行，事实有 provenance；
- 无 LLM 也能工作，域外问题明确拒答；
- Agent 工具只读，SPARQL 仅允许 SELECT/ASK，最多 8 轮；
- OpenSpec 和 pytest 将能力问题转为机械验收。

### 7.2 需要明确的边界

- 只有 2 个对象关系，业务网络较稀疏；
- 没有 OWL restriction、互斥类和 SHACL 数据约束；
- 规则只有一条且阈值写在 Python 中；
- 检索是字符串/字符 bigram，不是真正 embedding 语义检索；
- API 无身份认证，CORS 为 `*`，运行时 LLM key 是进程级共享；
- 文件内存图无事务、增量刷新、高可用和多租户；
- `Rate`、`BankingEvent` 已建模但未出现在树根；
- 命名空间仍是占位域名；
- FIBO 对齐只有 13 个，而且部分只是近似术语映射；
- 当前“本体推理无冲突”不代表业务数据完整、正确或合规。

---

## 8. 建议的生产化路线图

### 阶段 A：把本体做成可治理的数据契约（2—4 周）

- 替换正式 IRI；
- 写清能力问题、owner、术语状态和变更策略；
- 增加 SHACL shapes 与 CI 门禁；
- 为类、关系、规则、mapping 建版本；
- 先选 5—10 条真正有价值的对象关系；
- 修复树入口、前端历史、依赖 warning 等 MVP 问题。

验收：每次 schema 改动可 diff、验证、评审、回滚；无 owner/定义/来源的概念不得发布。

### 阶段 B：接入真实数据而不破坏语义层（4—8 周）

- 设计稳定实体 ID 和 entity resolution；
- 用声明式 mapping 连接产品、客户、账户等授权数据；
- 记录 source system、source key、event time、ingestion time；
- 区分虚拟查询与物化索引；
- 建增量刷新、质量报表和 lineage；
- 切换到持久图数据库或三元组库。

验收：同一对象跨源可识别；数据刷新 SLA 明确；来源可追溯；删除/更正可传播。

### 阶段 C：增加 Palantir 式操作闭环（4—8 周）

建议先做 2—3 个低风险 Action：

1. 提交术语新增/变更审核；
2. 发起产品信息纠错工单；
3. 生成合规复核任务。

每个 Action 必须包含参数校验、前置条件、读写权限、幂等、审计、状态机、失败补偿。Agent 只能调用经过授权的 Action API，不能直接获得任意写权限。

验收：每次动作可回答“谁、何时、基于哪些事实、执行了什么、结果如何、能否撤销”。

### 阶段 D：安全地服务 AI（持续）

- RAG 只检索调用者有权读取的对象；
- 工具按用户身份执行并记录 trace；
- 外部模型数据出域分级；
- 提示词、引用、工具参数和输出均审计；
- 建事实正确率、引用覆盖率、拒答率、动作成功率评测；
- 不假设源数据行级过滤会自动传播到导出、Function、Action 或 AI 上下文。

---

## 9. 推荐验收清单

### 模型

- [ ] 每个核心类有稳定 IRI、中英标签、定义、来源、owner；
- [ ] 分类轴明确，无循环层级；
- [ ] 属性有类型、单位、基数和敏感等级；
- [ ] 外部映射区分 exact/close/broad/narrow，不滥用等价；
- [ ] schema 与 instance 分离。

### 数据与推理

- [ ] mapping、主键、刷新和 lineage 可追溯；
- [ ] SHACL 验证通过；
- [ ] OWL/HermiT 一致性通过；
- [ ] 推理事实带 provenance 和解释；
- [ ] 规则有 owner、版本、有效期和反例测试。

### 应用与安全

- [ ] 搜索、查询和 Agent 均做权限裁剪；
- [ ] SPARQL 更新默认禁止；
- [ ] Action 有前置条件、授权、幂等、审计和补偿；
- [ ] LLM 失败时可降级，域外问题可拒答；
- [ ] schema 变更走 branch/working copy → diff → review → publish → rollback。

---

## 10. 最终结论

复现本项目时，应先复现“问题驱动的语义建模和验证闭环”，再复现界面和 LLM：

```text
业务问题
→ 稳定概念与关系
→ TBox/ABox/mapping 分层
→ 来源与标准对齐
→ SHACL/OWL/查询测试
→ API 和应用
→ Action、权限、审计
→ AI Agent
```

本项目已经是一个合格的本体知识库 MVP，也是理解 RDF/OWL、推理、语义检索和受约束 Agent 的良好起点。下一步若要达到企业最新实践，不应继续单纯堆类和三元组，而应优先补齐**真实数据绑定、版本审批、SHACL、对象级安全以及可审计 Action**。这五项决定它能否从“知识演示”升级为真正参与业务决策与执行的本体平台。

## 参考资料

### 仓库内

- `README.md`
- `ontology/banking-core.ttl`
- `ontology/seed-corpora.ttl`
- `ontology/fibo-alignment.ttl`
- `docs/fibo-alignment.md`
- `docs/reference/ontology-sources.md`
- `openspec/changes/archive/2026-09-09-banking-concept-kb-mvp/design.md`

### 厂商官方资料

- [Palantir Ontology — Core concepts](https://www.palantir.com/docs/foundry/ontology/core-concepts/)
- [Palantir — Object and link types](https://www.palantir.com/docs/foundry/object-link-types/type-reference)
- [Palantir — Action types](https://www.palantir.com/docs/foundry/action-types/overview/)
- [Palantir — Ontology branching](https://www.palantir.com/docs/foundry/ontologies/branching-ontology/)
- [Stardog — Virtual Graphs](https://docs.stardog.com/virtual-graphs/)
- [Stardog — Inference Engine](https://docs.stardog.com/inference-engine/)
- [Stardog — Ontology Maintenance & Data Mapping](https://docs.stardog.com/voicebox/guided-ontology-creation-and-mapping/)
- [TopQuadrant — Overview of TopBraid EDG Ontologies](https://www.topquadrant.com/blog/overview-of-topbraid-edg-ontologies)
- [Graphwise / PoolParty — System Architecture](https://help-dev.poolparty.biz/en/poolparty-overview/graphwise-platform-system-architecture.html)
- [Microsoft Fabric — Ontology (Preview)](https://learn.microsoft.com/en-gb/fabric/iq/ontology/overview)
