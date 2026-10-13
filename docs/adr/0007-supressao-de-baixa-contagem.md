# ADR 0007 — Supressão de baixa contagem antes de publicar

**Status:** aceito

## Contexto

O [ADR 0004](0004-base-legal-dados-de-ocorrencias.md) autorizou o uso das ocorrências da Guarda Municipal sob a condição de que "células com contagem muito baixa são suprimidas ou suavizadas antes de publicar", com o limiar decidido na Fase 2, antes do primeiro mapa. "Uma ocorrência neste lugar" pode identificar uma vítima.

Duas coisas mudaram desde aquele texto:

- **A unidade não é a célula H3, é o bairro.** A base da Guarda não tem coordenada: o menor lugar que ela registra é o bairro, e cada hexágono só repete a nota do seu bairro. Suprimir por célula não protegeria nada que a supressão por bairro já não proteja.
- **A suavização não basta.** O Bayes empírico (Fase 2) puxa as taxas instáveis para a média, mas se inverte: com a população do Censo, que é pública, e o κ documentado, a taxa suavizada devolve a gravidade observada.

## Decisão

**Nada sai do projeto sem passar por `processing/supressao.py`, com limiar de 5 ocorrências.**

1. **Bairro com menos de 5 ocorrências** de interesse, no período inteiro, sai sem contagem, taxas, nota e classe, marcado `suprimido`. A população fica, porque é do Censo.
2. **Supressão complementar.** O total da cidade é público, então a soma dos bairros suprimidos se obtém por diferença. Cada suprimido tem entre 0 e 4 ocorrências; se a soma for tal que todos tenham ao menos uma — com um suprimido só, o valor sai exato —, o bairro publicado de menor contagem também é suprimido.
3. **Nenhuma subcontagem por bairro.** Nem por tipo, nem por mês, nem a fração em equipamento urbano. Suprimir só as células baixas de uma tabela bairro × tipo não basta: o total do bairro menos os outros tipos devolve a escondida. Tipo só sai somado para a cidade, com o mesmo limiar e o mesmo complemento.
4. **O mapa mostra a supressão.** Bairro suprimido aparece em cinza com hachura, na direção oposta à de "sem dado", com a legenda "suprimido: menos de 5 ocorrências". Não aparece como "baixo": seria afirmar o que a contagem não sustenta.
5. **Barreira final em código.** `supressao.verificar` roda antes de gravar cada arquivo publicado e para se encontrar contagem por tipo em tabela por lugar, contagem abaixo de 5, ou linha suprimida com algum valor.
6. **SESP-PR só com autorização explícita.** Os agregados da SESP passam pela mesma regra, mas só são gravados se o ADR 0006 contiver a linha `Publicação de agregados: permitida`. Usar e publicar são autorizações diferentes, e a resposta da LAI pode dar uma sem a outra. Se ela impuser limiar maior, vale o dela.

O que fica em `data/processed/` continua completo e fora do Git: as fases seguintes calculam com todos os bairros. O que é publicado vai para `data/publicado/`, a única pasta de dados versionada.

## Justificativa

**Por que 5.** Limiares entre 3 e 10 são comuns na divulgação de estatística oficial. O código já usava 5 para marcar `baixa_contagem`, o ponto em que a taxa deixa de ser estável — a mesma fronteira serve às duas razões. O custo de subir foi medido com a base da Guarda:

| Limiar | Bairros suprimidos |
|---|---:|
| menos de 5 | 5 |
| menos de 10 | 10 |
| menos de 20 | 25 |

Com 10, o mapa perde o dobro de bairros sem ganho de proteção proporcional: a contagem já é do período inteiro (2023 em diante) e soma todos os tipos, o que dilui a ligação entre o número e uma pessoa.

**Por que zero também é suprimido.** Um bairro sem ocorrência não expõe ninguém, mas sua taxa é a menos estável de todas, e publicar os zerados encolheria o grupo dos suprimidos — e quanto menor o grupo, mais a soma obtida por diferença revela sobre cada um.

## Consequências

- Com a base da Guarda, 5 bairros saem suprimidos: Lamenha Pequena e Riviera (0 ocorrências), Ahú (3), Caximba e Jardim Social (4). A soma deles, 11, não permite deduzir nenhum, então não há complemento.
- O mapa de classe passa a ter três estados: alto, baixo e suprimido. A classe dos demais não muda — a mediana continua sendo a dos 75 bairros.
- A comparação Guarda × SESP suprime o bairro que estiver suprimido em qualquer das duas.
- Quem quiser auditar tem `data/publicado/` e o código; o dado completo só se reconstrói baixando a base pública da Guarda e rodando o pipeline — que é o que o ADR 0004 já permitia.
