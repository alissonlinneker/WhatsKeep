# Pesquisa: Provas Digitais no Brasil — WhatsApp como Evidência Judicial

> Pesquisa realizada em abril/2026. Foco em legislação, jurisprudência recente (2024-2026),
> métodos de preservação e implicações para o projeto WhatsKeep.

---

## 1. Legislação Aplicável

### 1.1 Marco Civil da Internet (Lei 12.965/2014)
- **Art. 7°**: Garante inviolabilidade e sigilo das comunicações privadas (incluindo WhatsApp)
- **Art. 10**: Guarda de registros de acesso a aplicações de internet — preservação por provedor
- **Art. 22**: Requisição judicial de registros para formação de conjunto probatório
- **Relevância para WhatsKeep**: O Marco Civil protege a privacidade das comunicações. A coleta de provas pelo próprio participante da conversa é lícita (não viola sigilo de terceiro), mas interceptação ou espelhamento por terceiro sem autorização judicial é ilícita.

### 1.2 CPC 2015 (Código de Processo Civil)
- **Art. 369**: Admite todos os meios legais e moralmente legítimos para provar fatos — inclui provas digitais
- **Art. 411, II**: Presunção de autenticidade de documentos com certificação eletrônica (ICP-Brasil ou outro meio legal)
- **Art. 422, §1°**: Documento eletrônico impugnado → cabe autenticação eletrônica ou perícia
- **Art. 441**: Documentos eletrônicos são admitidos se produzidos e preservados conforme legislação específica
- **Art. 384**: Ata notarial — tabelião atesta existência e estado de coisas (base legal para ata notarial digital)
- **Relevância**: No cível, o ônus de provar falsidade recai sobre quem impugna. Print de WhatsApp sem ata notarial pode ser aceito se não impugnado, mas é frágil.

### 1.3 Lei 13.964/2019 (Pacote Anticrime) — Cadeia de Custódia
- **Art. 158-A**: Define cadeia de custódia como "conjunto de todos os procedimentos utilizados para manter e documentar a história cronológica do vestígio"
- **Art. 158-B**: Lista 10 etapas obrigatórias: reconhecimento, isolamento, fixação, coleta, acondicionamento, transporte, recebimento, processamento, armazenamento, descarte
- **Art. 158-C**: Vestígio deve ser acondicionado em recipiente adequado, lacrado, identificado
- **Art. 158-D**: Recipiente deve ser auditável, com número de lacre, responsável, natureza do vestígio
- **Art. 158-F**: Peritos que reconhecerem vestígio devem comunicar à autoridade
- **Relevância para software**: Essas etapas foram pensadas para vestígios físicos, mas o STJ as aplica a provas digitais. Um software pode automatizar fixação (hash), coleta (cópia), acondicionamento (armazenamento seguro) e documentação (log de cadeia).

### 1.4 MP 2.200-2/2001
- Institui a ICP-Brasil (Infraestrutura de Chaves Públicas)
- **Art. 10, §2°**: Admite documentos eletrônicos com outras formas de certificação além da ICP-Brasil, desde que aceitas pelas partes ou por lei
- **Relevância**: Fundamenta a validade de assinaturas digitais e certificações por blockchain, hash SHA-256, etc.

### 1.5 ABNT NBR ISO/IEC 27037:2013
- Norma técnica (não lei, mas referenciada pelo STJ) para identificação, coleta, aquisição e preservação de evidência digital
- 4 requisitos fundamentais: **Auditabilidade, Repetibilidade, Reprodutibilidade, Justificabilidade**
- Citada expressamente em decisões do STJ como padrão esperado

---

## 2. Jurisprudência do STJ e STF sobre WhatsApp

### 2.1 Decisões que INVALIDARAM provas de WhatsApp

#### HC 828.054/RN — 5ª Turma (Maio/2024)
- **Contexto**: Prints de celular extraídos pela polícia sem metodologia adequada
- **Decisão**: Inadmissíveis. Faltou ferramenta forense, hash, documentação de cadeia de custódia
- **Fundamento**: Art. 158-A a 158-F CPP, ISO 27037
- **Impacto**: Marco decisório — "provas digitais devem ser colhidas com metodologia adequada"

#### HC 1.036.370 — Min. Joel Ilan Paciornik (Setembro/2025)
- **Contexto**: Condenação por roubo qualificado baseada em prints de WhatsApp do celular de corréu
- **Decisão**: Condenação **anulada**. Prints sem documentação de coleta, preservação ou verificação
- **Fundamento**: Ausência total de cadeia de custódia digital
- **Impacto**: "Fim da era do print de WhatsApp como prova penal" — termo usado pela doutrina

#### 6ª Turma — Dezembro/2024
- **Decisão**: Ausência rigorosa de cadeia de custódia torna provas digitais inválidas e nulas
- **Paradigma**: Aplicável tanto na esfera penal quanto cível

#### Espelhamento via WhatsApp Web — 6ª Turma (2021, reafirmado depois)
- **Decisão**: Prova obtida por espelhamento de WhatsApp Web é **inválida** como meio de interceptação
- **Fundamento**: Espelhamento permite manipulação em tempo real (apagar/enviar mensagens)

### 2.2 Decisões que ACEITARAM provas de WhatsApp

#### 5ª Turma — Prints de particular (2025)
- **Contexto**: Prints de WhatsApp obtidos por particular (vítima de violência doméstica)
- **Decisão**: Válidos, desde que **confirmados em juízo** e **sem indícios de adulteração**
- **Distinção crucial**: Cadeia de custódia estrita aplica-se ao **Estado** (polícia, MP). Particular tem flexibilidade maior, mas não imunidade

#### STJ — Assinaturas fora da ICP-Brasil (Setembro/2024)
- **Decisão**: Assinaturas digitais com SHA-256 em plataformas privadas são válidas
- **Fundamento**: Exigir ICP-Brasil em todos os casos seria "formalismo excessivo"

### 2.3 Síntese Jurisprudencial

| Situação | Resultado | Condições |
|----------|-----------|-----------|
| Print policial sem hash/cadeia | ❌ Inválido | Esfera penal — rigor total |
| Print particular sem impugnação | ✅ Válido | Cível — se não contestado |
| Print particular impugnado | ⚠️ Depende | Precisa perícia ou autenticação |
| Print particular + ata notarial | ✅ Forte | Fé pública do tabelião |
| Print particular + Verifact | ✅ Aceito | Reconhecido nas 3 instâncias |
| Print com hash + blockchain | ✅ Aceito | TJSP já reconheceu (OriginalMy) |
| Espelhamento WhatsApp Web | ❌ Inválido | Interceptação ilícita |
| Particular + confirmação em juízo | ✅ Válido | Violência doméstica, sem adulteração |

---

## 3. Ata Notarial para Conteúdo Digital

### 3.1 O que é
- Documento lavrado por tabelião (notário) com **fé pública**
- Atesta a existência e o conteúdo de uma situação de fato no momento da lavratura
- Base legal: **Art. 384, CPC/2015** e **Lei 8.935/94**
- O tabelião **não opina** sobre o mérito — apenas registra o que vê/ouve

### 3.2 Como funciona para WhatsApp
1. Você vai ao cartório de notas com o celular
2. O tabelião acessa as conversas no dispositivo
3. Registra screenshots, transcrições, metadados visíveis
4. Lavra a ata com descrição detalhada
5. Documento recebe assinatura e selo do cartório

### 3.3 Custos (2025-2026)
| Estado | Primeira folha | Folha adicional |
|--------|---------------|-----------------|
| São Paulo | R$ 615,49 | R$ 296,63 |
| Média nacional | R$ 100 — R$ 200 | Variável |
| **Total típico** | **R$ 500 — R$ 2.000+** | Depende do volume |

### 3.4 Limitações
- **Caro**: Para muitas conversas/mídia, o custo escala rapidamente
- **Presencial**: Exige ir ao cartório (em regra) — embora o e-Not Provas mude isso
- **Ponto no tempo**: Atesta o que existe no momento. Se o conteúdo for deletado antes da ida ao cartório, perdeu-se
- **Não é perícia forense**: O tabelião não verifica integridade técnica (hash, metadados internos)
- **Dependência humana**: A qualidade depende do tabelião — alguns são mais detalhistas que outros

### 3.5 e-Not Provas (Novidade 2026)
- Serviço do **Colégio Notarial do Brasil**
- Coleta e preservação de provas digitais **online**, sob supervisão de tabelião
- **Preço**: R$ 4 a R$ 7 por captura (dependendo do estado)
- **Disponível nacionalmente** desde janeiro/2026
- Captura páginas web, WhatsApp Web, redes sociais
- Armazenamento por 5 anos
- **Vantagem**: Custo muito inferior à ata notarial tradicional, com fé pública

---

## 4. Métodos Técnicos de Preservação Aceitos

### 4.1 Hash (SHA-256)
- **O que faz**: Gera "impressão digital" única do arquivo. Qualquer alteração muda o hash completamente
- **Aceito por tribunais**: Sim, STJ cita como requisito para cadeia de custódia
- **Limitação crítica**: Hash **sozinho não é suficiente**. Ele prova integridade (o arquivo não mudou), mas NÃO prova:
  - Quando o hash foi gerado (sem carimbo de tempo)
  - Quem gerou o hash
  - Que o conteúdo original é autêntico (hash de um arquivo fabricado continua sendo um hash válido)
- **Melhor prática**: SHA-256 + carimbo de tempo + assinatura digital = trio mínimo

### 4.2 Blockchain Timestamping
- **OpenTimestamps**: Gratuito, âncora no Bitcoin. Prova que um hash existia em determinado momento
- **OriginStamp**: Similar, com API. Âncora em múltiplas blockchains
- **Status judicial**: O TJSP aceitou prova certificada por blockchain (caso OriginalMy). Não é mainstream, mas tem precedente
- **Vantagem**: Imutável, verificável publicamente, não depende de uma empresa específica
- **Limitação**: Prova existência temporal do hash, não autenticidade do conteúdo em si

### 4.3 ICP-Brasil (Certificado Digital Brasileiro)
- **Padrão-ouro** para assinatura digital no Brasil
- Presunção legal de autenticidade (MP 2.200-2/2001, Art. 10, §1°)
- Carimbo de tempo ICP-Brasil é aceito sem contestação
- **Custo**: Certificado A1 ~R$ 150-300/ano; A3 ~R$ 200-500/ano
- **Limitação**: STJ já disse que exigir ICP-Brasil sempre seria "formalismo excessivo" — outros métodos são válidos

### 4.4 Combinação Ideal (Robustez Máxima)
```
Arquivo Original
    → SHA-256 hash
        → Carimbo de tempo ICP-Brasil (ou blockchain)
            → Assinatura digital (ICP-Brasil ou SHA-256 aceita)
                → Metadados documentados (quem, quando, como, dispositivo)
                    → Log de cadeia de custódia
```

---

## 5. Plataformas Brasileiras para Preservação de Provas Digitais

### 5.1 Verifact (líder de mercado)
- **Site**: https://www.verifact.com.br
- **Preço**: R$ 97/sessão (50 capturas, 50MB de arquivos, 30min de vídeo)
- **Como funciona**: Navegação em ambiente isolado nos servidores da Verifact. Impede manipulação local
- **Saída**: Relatório técnico certificado + vídeo de navegação + metadados auditáveis + carimbo ICP-Brasil
- **Conformidade**: ISO 27037, cadeia de custódia do CPP
- **Aceitação judicial**: Reconhecido nas 3 instâncias (1ª, 2ª e Superior)
- **Suporta**: WhatsApp Web, Instagram, Facebook, Twitter/X, Telegram, sites, e-mails
- **Diferencial**: Único que demonstrou prevenir fraude na coleta (ambiente isolado server-side)
- **Limitação**: Funciona apenas para conteúdo acessível via navegador web. Não acessa o app nativo do WhatsApp Desktop

### 5.2 DataCertify
- **Site**: https://www.datacertify.com.br
- **Como funciona**: Software/plugin no computador do usuário + hash + blockchain
- **Vantagem**: Foco em facilidade de uso, integração com advogados
- **Problema**: Análise forense (Academia de Forense Digital) mostrou que **não previne manipulação no ambiente local** — o software roda na máquina do usuário, que pode ser comprometida
- **Conformidade ISO 27037**: Parcial/Questionável

### 5.3 OriginalMy (PACDigital / PACWeb)
- **Site**: https://originalmy.com
- **Como funciona**: PACDigital certifica arquivos via blockchain. PACWeb captura páginas web
- **Aceitação**: TJSP reconheceu validade de prova certificada por PACWeb
- **Problema**: Mesmo da DataCertify — plugin no navegador do usuário, sem isolamento de ambiente
- **Conformidade ISO 27037**: Parcial/Questionável

### 5.4 e-Not Provas (Colégio Notarial)
- **Preço**: R$ 4-7 por captura
- **Diferencial**: Fé pública do tabelião + preço acessível
- **Novo**: Disponível desde janeiro/2026
- **Ideal para**: Volume grande de capturas a baixo custo

### 5.5 Capturee
- **Site**: https://capturee.io
- **Alternativa** ao Verifact, mais recente no mercado
- **Posiciona-se** como solução de coleta forense com cadeia de custódia

### 5.6 Comparativo Resumido

| Plataforma | Preço | Ambiente Isolado | ISO 27037 | Blockchain | Fé Pública | Aceitação Judicial |
|------------|-------|-----------------|-----------|-----------|-----------|-------------------|
| Verifact | R$ 97/sessão | ✅ Server-side | ✅ Completa | ❌ | ❌ | ✅ Consolidada |
| DataCertify | Variável | ❌ Client-side | ⚠️ Parcial | ✅ | ❌ | ✅ Existente |
| OriginalMy | Variável | ❌ Client-side | ⚠️ Parcial | ✅ | ❌ | ✅ TJSP |
| e-Not Provas | R$ 4-7/captura | ✅ Remoto | N/A | ❌ | ✅ Tabelião | ✅ Nova |
| Ata Notarial | R$ 500-2000+ | N/A (presencial) | N/A | ❌ | ✅ Tabelião | ✅ Consolidada |

---

## 6. Cadeia de Custódia Digital na Prática

### 6.1 O que o STJ exige (Art. 158-A a 158-F adaptado ao digital)

1. **Reconhecimento**: Identificar que há evidência digital a ser preservada
2. **Isolamento**: Isolar o dispositivo/dados da rede para evitar alteração remota
3. **Fixação**: Gerar hash (SHA-256 mínimo) do conteúdo original antes de qualquer manipulação
4. **Coleta**: Copiar/extrair dados com ferramenta forense validada
5. **Acondicionamento**: Armazenar em mídia confiável, lacrada/protegida
6. **Transporte**: Documentar quem moveu, quando, como
7. **Recebimento**: Registrar entrada no local de análise/armazenamento
8. **Processamento**: Análise sem alterar o original (trabalhar em cópia)
9. **Armazenamento**: Preservar com controle de acesso e integridade verificável
10. **Descarte**: Documentar destruição quando aplicável

### 6.2 Mínimo Viável para Prova Digital Robusta

| Requisito | Mínimo Aceitável | Ideal |
|-----------|------------------|-------|
| Hash | SHA-256 do arquivo | SHA-256 + SHA-512 |
| Carimbo temporal | Timestamp com fonte confiável | ICP-Brasil ou blockchain |
| Metadados | Data, hora, nome do arquivo | + dispositivo, SO, usuário, IP, geolocalização |
| Cadeia de custódia | Log de quem/quando/como | Log assinado digitalmente |
| Integridade | Hash gerado na coleta | Hash + verificação periódica |
| Armazenamento | Cópia segura | Original isolado + cópia de trabalho |
| Contexto | Descrição do conteúdo | + relação com caso, participantes, conversação completa |

### 6.3 Esfera Penal vs. Cível

| Aspecto | Penal | Cível | Trabalhista |
|---------|-------|-------|-------------|
| Cadeia de custódia | Obrigatória (CPP) | Recomendada/crescente | Crescente |
| Ônus da prova | Estado deve provar integridade | Quem impugna deve provar falsidade | Similar ao cível |
| Print simples | ❌ Cada vez mais rejeitado | ✅ Se não impugnado | ⚠️ Variável |
| Ata notarial | Forte, mas insuficiente sozinha | Muito forte | Forte |
| Hash/blockchain | Exigido para evidência policial | Recomendado | Recomendado |
| Consequência de falha | Nulidade/absolvição | Perda do valor probatório | Perda do valor probatório |

---

## 7. Casos Reais de Invalidação

### Caso 1: HC 828.054/RN (Maio/2024) — STJ, 5ª Turma
- **O que aconteceu**: Polícia fez prints de celular sem ferramenta forense
- **Resultado**: Provas **inadmissíveis**
- **Lição**: Printscreen policial sem hash, sem Cellebrite, sem documentação = nulo

### Caso 2: HC 1.036.370 (Setembro/2025) — STJ
- **O que aconteceu**: Condenação por roubo qualificado baseada apenas em prints de WhatsApp
- **Resultado**: Condenação **anulada integralmente**
- **Lição**: Sem documentação de coleta/preservação/verificação → prova inexistente

### Caso 3: Espelhamento WhatsApp Web (2021, reafirmado)
- **O que aconteceu**: Investigador espelhou WhatsApp via QR code do WhatsApp Web
- **Resultado**: Prova **inválida** — equiparado a interceptação ilícita
- **Lição**: Acesso ao WhatsApp de terceiro sem autorização judicial é ilegal

### Caso 4: 6ª Turma STJ (Dezembro/2024)
- **O que aconteceu**: Provas digitais sem cadeia de custódia rigorosa
- **Resultado**: **Nulas** — novo paradigma para admissibilidade
- **Lição**: Tendência irreversível de exigência de rigor técnico

### Caso 5: TJSP — OriginalMy/Blockchain (2019)
- **O que aconteceu**: Político tentou remover posts de redes sociais. Prova certificada por blockchain
- **Resultado**: Prova **aceita** — juíza reconheceu que blockchain garante integridade
- **Lição**: Métodos modernos de preservação já são aceitos

---

## 8. O Que um Software (como o WhatsKeep) Pode e NÃO Pode Fazer

### 8.1 O Que PODE Fazer (e é valioso)

1. **Gerar hash SHA-256 automaticamente** de cada arquivo de mídia no momento da cópia
2. **Registrar metadados completos**: timestamp do arquivo, timestamp da cópia, dispositivo, SO, usuário do SO, caminho original
3. **Criar log de cadeia de custódia**: quem copiou, quando, de onde, para onde, hash antes/depois
4. **Preservar estrutura**: Manter relação arquivo ↔ contato ↔ grupo ↔ data
5. **Carimbo temporal verificável**: Anchor hash em blockchain (OpenTimestamps) ou solicitar TSA de ICP-Brasil
6. **Verificação de integridade**: Checar periodicamente que os hashes não mudaram
7. **Gerar relatório forense**: Exportar cadeia de custódia em formato estruturado (JSON/PDF)
8. **Organizar por contato/grupo**: Facilitar localização e apresentação de evidências
9. **Monitoramento contínuo**: Capturar mídias automaticamente antes que sejam deletadas

### 8.2 O Que NÃO Pode Fazer (limitações inerentes)

1. **NÃO substitui ata notarial**: O software não tem fé pública. Seu relatório é evidência técnica, não documento público
2. **NÃO garante autenticidade do conteúdo original**: O hash prova que o arquivo não foi alterado DEPOIS da cópia, mas não prova que o conteúdo original do WhatsApp é autêntico (poderia ter sido fabricado antes da cópia)
3. **NÃO é ambiente isolado**: Como roda na máquina do usuário (como DataCertify/OriginalMy), um perito pode argumentar que o ambiente poderia estar comprometido
4. **NÃO substitui perícia forense**: Em caso de contestação séria, um perito judicial será necessário
5. **NÃO opera no DB do WhatsApp com fé pública**: A leitura do SQLite é read-only, mas um adversário pode argumentar que o DB foi manipulado antes da leitura
6. **NÃO garante conformidade ISO 27037 completa**: Falta auditabilidade independente e reprodutibilidade por terceiro
7. **NÃO faz interceptação legal**: Não pode acessar conversas de terceiros

### 8.3 Posicionamento Realista do WhatsKeep

O WhatsKeep é uma **ferramenta de organização e backup** que **pode auxiliar na preservação de evidências**, mas **não é uma ferramenta forense certificada**.

**Valor real para o usuário:**
- Preservar mídias que seriam perdidas (WhatsApp apaga automaticamente)
- Organizar por contato/grupo para facilitar localização
- Gerar hash e metadados como **primeira camada de preservação**
- Servir como **base** para posterior certificação por ata notarial, Verifact ou e-Not Provas

**Analogia**: O WhatsKeep é como fazer uma cópia de segurança organizada de seus documentos. Se você precisar usar esses documentos em tribunal, a cópia é útil, mas você ainda pode precisar autenticá-la formalmente.

### 8.4 Estratégia de Camadas para o Usuário

```
Camada 1 (Automática - WhatsKeep):
    → Backup organizado + hash SHA-256 + metadados + log de cadeia de custódia
    → Custo: Gratuito (software open-source)
    → Valor: Preservação contra perda, organização, base técnica

Camada 2 (Opcional - Baixo Custo):
    → Hash ancorado em blockchain (OpenTimestamps)
    → Custo: Gratuito
    → Valor: Prova temporal imutável de que o conteúdo existia naquele momento

Camada 3 (Recomendada - Quando há risco judicial):
    → Verifact (R$ 97/sessão) ou e-Not Provas (R$ 4-7/captura)
    → Custo: Baixo a moderado
    → Valor: Cadeia de custódia independente, aceita em tribunal

Camada 4 (Máxima - Litígio sério):
    → Ata notarial completa (R$ 500-2000+) + perícia forense
    → Custo: Alto
    → Valor: Fé pública + análise técnica especializada
```

---

## 9. Recomendações para o WhatsKeep

### 9.1 Funcionalidades de Valor Jurídico a Implementar
1. **Hash SHA-256 automático** de cada arquivo no momento da cópia (já previsto na arquitetura)
2. **Log de cadeia de custódia** em formato JSON/CSV com campos: arquivo, hash_origem, hash_destino, timestamp_cópia, usuário_SO, hostname, caminho_origem, caminho_destino
3. **Verificação de integridade**: Comando `whatskeep verify` que re-calcula hashes e compara com log
4. **Relatório exportável**: `whatskeep report --format pdf` com sumário de cadeia de custódia
5. **Integração opcional com OpenTimestamps**: Ancorar hashes em blockchain automaticamente
6. **Aviso ao usuário**: Informar claramente que o backup WhatsKeep é um primeiro passo, não substituto de certificação formal

### 9.2 Disclaimer Obrigatório (Sugestão)
> "O WhatsKeep é uma ferramenta de backup e organização de mídias. Os hashes e metadados gerados auxiliam na preservação de integridade, mas não substituem ata notarial, perícia forense ou plataformas certificadas (como Verifact) para uso como prova judicial. Consulte um advogado para orientação sobre preservação de evidências no seu caso específico."

### 9.3 O que NÃO fazer
- NÃO afirmar que o WhatsKeep gera "provas judiciais válidas"
- NÃO usar termos como "forense" ou "certificado" sem qualificação
- NÃO prometer conformidade ISO 27037 (seria preciso auditoria independente)
- NÃO sugerir que substitui serviços profissionais

---

## 10. Fontes e Referências

### Legislação
- [Lei 12.965/2014 — Marco Civil da Internet](http://www.planalto.gov.br/ccivil_03/_ato2011-2014/2014/lei/l12965.htm)
- [Lei 13.105/2015 — CPC](http://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13105.htm)
- [Lei 13.964/2019 — Pacote Anticrime](http://www.planalto.gov.br/ccivil_03/_ato2019-2022/2019/lei/l13964.htm)
- [MP 2.200-2/2001 — ICP-Brasil](http://www.planalto.gov.br/ccivil_03/mpv/antigas_2001/2200-2.htm)

### Jurisprudência STJ
- [STJ — Provas digitais devem ser colhidas com metodologia adequada (Maio/2024)](https://www.stj.jus.br/sites/portalp/Paginas/Comunicacao/Noticias/2024/02052024-Quinta-Turma-nao-aceita-como-provas-prints-de-celular-extraidos-sem-metodologia-adequada.aspx)
- [STJ anula condenação por ausência de integralidade da prova digital (Nov/2025)](https://www.conjur.com.br/2025-nov-07/stj-anula-condenacao-por-ausencia-de-integralidade-da-prova-digital/)
- [STJ — Prints de particular válidos sem indícios de adulteração](https://evinistalon.com/stj-prints-de-whatsapp-confirmados-em-juizo-e-sem-indicios-de-adulteracao-nao-violam-a-cadeia-de-custodia/)
- [STJ — Espelhamento WhatsApp Web inválido](https://www.stj.jus.br/sites/portalp/Paginas/Comunicacao/Noticias/09032021-Sexta-Turma-reafirma-invalidade-de-prova-obtida-pelo-espelhamento-de-conversas-via-WhatsApp-Web.aspx)
- [STJ admite assinaturas digitais fora da ICP-Brasil](https://www.migalhas.com.br/quentes/451284/stj-admite-assinaturas-digitais-fora-da-icp-brasil-entenda-o-tema)
- [Cadeia de Custódia em 2026: O que o STJ Decidiu](https://stwbrasil.com/blog/cadeia-de-custodia-em-2026-o-que-o-stj-decidiu-sobre-provas-digitais-e-prints-de-whatsapp-no-processo-penal/)

### Análises e Doutrina
- [Migalhas — Uso de prova de prints de WhatsApp à luz da jurisprudência do STJ](https://www.migalhas.com.br/coluna/migalhas-criminais/445874/uso-de-prova-de-prints-de-whatsapp-a-luz-da-jurisprudencia-do-stj)
- [Conjur — Verifact e a evolução da prova digital](https://www.conjur.com.br/2025-ago-17/verifact-e-a-evolucao-da-prova-digital-no-processo-judicial/)
- [Conjur — Distribuição do ônus da prova na cadeia de custódia digital](https://www.conjur.com.br/2025-out-15/a-distribuicao-do-onus-da-prova-no-ambito-da-cadeia-de-custodia-da-prova-digital/)
- [Conjur — Admissibilidade de conversas de WhatsApp como meio de prova](https://www.conjur.com.br/2024-jul-17/admissibilidade-de-conversas-de-whatsapp-como-meio-de-prova/)
- [Academia de Forense Digital — Testamos 3 ferramentas de prova digital](https://academiadeforensedigital.com.br/provas-digitais-avaliando-3-ferramentas/)
- [DataCertify — Por que o hash sozinho não é suficiente](https://www.datacertify.com.br/por-que-o-hash-por-si-so-nao-e-suficiente/)
- [CNJ — Justiça do Trabalho pioneira no uso de provas digitais](https://www.cnj.jus.br/justica-do-trabalho-e-pioneira-no-uso-de-provas-digitais-em-processos/)

### Plataformas
- [Verifact](https://www.verifact.com.br/)
- [DataCertify](https://www.datacertify.com.br/)
- [OriginalMy](https://originalmy.com/)
- [e-Not Provas — Colégio Notarial do Brasil](https://www.notariado.org.br/e-not-provas-novo-servico-digital-viabiliza-autenticacao-de-provas-online-a-partir-de-r-4/)
- [Capturee](https://capturee.io/)

### Normas Técnicas
- ABNT NBR ISO/IEC 27037:2013 — Diretrizes para identificação, coleta, aquisição e preservação de evidência digital
