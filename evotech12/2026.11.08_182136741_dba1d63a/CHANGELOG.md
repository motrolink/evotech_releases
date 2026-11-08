# evotech12 2026.11.08

Placa: evotech12 · Canal: desenvolvimento · Data: 2026-11-08 · Build: dba1d63a

> Prévia: notas de uma build de desenvolvimento, ainda não publicadas como versão estável.

> ATENÇÃO: esta atualização APAGA a configuração da ECU. Exporte o mapa antes de atualizar.

## Novidades

- **Acoplamento entre o enriquecimento de aceleração e o filme de parede**
  Novos campos: parcela do enriquecimento que passa pelo filme (1,0 = como antes: o filme também amplifica o AE em
  1/(1-beta); 0,0 = o AE entra depois do filme), teto do enriquecimento de aceleração (0 = sem teto) e "Escalar a
  desaceleração pelas curvas de CLT e rotação". Eles reaproveitam os bytes de duas curvas 1D do filme que a ECU
  nunca lia. Um mapa salvo é convertido no carregamento (parcela 1,0, sem teto, desaceleração ainda escalada), então
  o comportamento se mantém; um mapa novo começa com a desaceleração sem escala.
  - Mapa: convertido automaticamente
  - Campos: `wwaeAeFilmShare`, `tpsAccelMaxEnrich`, `tpsDecelUsesCltRpmMult`, `aeCouplingMigrated`
  - O que fazer: O assistente do Manager que escrevia os campos antigos dessa curva precisa ser atualizado.
- **Telemetria do corte na troca**
  Canais novos: estado da velocidade, regra de velocidade inativa, porta de velocidade, % de corte de faísca, avanço usado
  durante o corte e o valor X atual de cada tabela, e o % de corte de faísca da largada. Os canais de telemetria mudam de
  posição nesta versão: use o INI que acompanha a firmware.
  - Para o preparador
- **evoNet 1.2: alertas de proteção, borboleta, sensores e falhas da ECU nos displays**
  O evoNet 1.2 envia proteções do motor, falhas da borboleta, de sensores e da ECU para displays compatíveis, com um alerta principal por severidade, medições ao vivo válidas e motivos separados de corte de combustível e de ignição. Os limites das proteções continuam configurados na ECU.
- **Tela Engine Geometry (menu Setup)**
  Único lugar para número de cilindros, cilindrada, diâmetro, ordem de ignição, estratégia de combustível, eficiência
  térmica, taxa de compressão e volumes de admissão e de escape até o sensor de lambda, agrupados em Dimensões do motor,
  Ciclo e combustão e Volumes (o diâmetro agora é editável sem detonação por software), com avisos de plausibilidade
  (curso 50 a 130 mm, diâmetro/curso 0,7 a 1,3) e um indicador de dados válidos. A geometria é sempre considerada
  confirmada: não há mais o bit "Geometry confirmed" nem mostrador de curso derivado. Esses campos saíram de Informações do
  veículo, que agora só tem a identificação. Canais novos: engineStrokeMm, engineGeometryInvalid, engineStrokeImplausible e
  engineBoreStrokeImplausible. Um mapa salvo com o bit antigo carrega com ele desmarcado; combustível e ignição não mudam.
  - Mapa: convertido automaticamente
  - O que fazer: Procure os campos de geometria na nova tela Engine Geometry.
- **Calibração do pedal e da borboleta a cabo por botões**
  Botões para calibrar o pedal solto e pisado e a borboleta fechada e totalmente aberta de uma borboleta a cabo,
  mais um status da calibração (procedimento, passo, progresso, resultado e contador de eventos) no TunerStudio
  e no Manager e um botão para abortar. A ECU recusa qualquer comando de calibração fora das condições (motor
  ligado, ignição ligada, sensor ausente ou fora da faixa, fechado e aberto muito próximos, outro procedimento
  em andamento, controle do motor da ETB pausado) e diz o motivo, em vez de falhar em silêncio.
- **Referência das funções Lua publicada com cada firmware**
  Cada release agora traz um arquivo com tudo o que um script Lua pode usar naquela firmware: as 92 funções, os
  ganchos onTick e onCanRx, os canais lidos por getOutput, os campos de getCalibration e setCalibration (com unidade e
  faixa), os sensores e o tamanho máximo do script. O Manager poderá usar esse arquivo para sugerir funções e conferir o
  script antes de gravar. Não muda nada no comportamento da ECU nem no seu mapa.
  - Para o preparador
- **Teto opcional de dwell da bobina (builds de desenvolvimento)**
  Um teto opcional de dwell cobre o dwell corrigido, a partida e o multispark, com prazo de saída independente e indicação de ajuste pendente. Ainda precisa de qualificação em bancada.
  - Mapa: campos novos com valor padrão
  - Campos: `maxDwellMs`
  - Para o preparador
- **Estado e erros do script Lua em canais de saída**
  A ECU passa a publicar o estado do script Lua (parado, rodando, erro ao carregar, erro em
  execução), a linha do último erro, o CRC32 do script carregado, a memória em uso e a
  contagem de erros. O Manager usa esses canais para mostrar o status do script e apontar a
  linha com problema, sem depender do texto do console. Os canais ficam no fim dos canais
  de saída e nenhum canal existente muda de posição.
  - Para o preparador
- **PWM senoidal da solenoide de marcha lenta (somente builds de desenvolvimento)**
  A válvula de marcha lenta pode ser acionada por uma senoide na Frequência da solenoide de marcha lenta (20 a 1000 Hz),
  sobre um PWM de hardware fixo de 20 kHz e com amplitude configurável. O duty médio continua igual à posição de marcha
  lenta comandada, então a calibração não muda; o sinal quadrado é mantido se o pino não tiver timer livre ou a
  frequência estiver fora da faixa (veja idle_pwm_info). Desligado por padrão. O efeito elétrico na válvula ainda não foi
  validado em bancada.
  - Mapa: campos novos com valor padrão
  - Campos: `idleSolenoidSineEnable`, `idleSolenoidSineAmplitude`
  - Para o preparador
- **OBD-II: PID 0x1F (tempo desde a partida)**
  O responder OBD-II responde ao PID 0x1F, informando 0 com o motor parado e os segundos decorridos com o motor funcionando. Displays como a WideLink, que usam esse PID na detecção de motor ligado para desligar sozinhos, passam a ter um terceiro sinal além de rotação e carga.
- **Osciloscópio de sinais com resolução de 1 us e até 8 canais**
  O Manager grava bordas digitais com resolução de 1 us e escolhe até 8 canais: gatilhos de virabrequim e comando, qualquer pino digital livre, bobinas e injetores por cilindro, PMS e sincronismo. As entradas de comando são gravadas pela primeira vez, o que torna possível diagnosticar a fase.
  - Para o preparador
- **Histórico das proteções e telas agrupadas por sistema**
  A visão geral das proteções guarda as oito últimas transições registradas no journal da ECU, com navegação, estado de
  gravação e exclusão do histórico. As telas são agrupadas por sistema e distinguem pedidos de proteção de restrições
  finais da ECU, com leituras numéricas ao vivo e causas e condições de liberação explícitas. Os campos de habilitação de
  proteção (água, ar de admissão, óleo e combustível, EGT, bateria, PFI e GDI) mostram opções booleanas em vez de 0/1,
  sem alterar os offsets da calibração. As configurações das proteções de duty do injetor passaram para a página do
  duty.
  - Mapa: campos novos com valor padrão
  - Campos: `epHistoryWords`, `cltTemperatureProtectionEnabled`, `iatTemperatureProtectionEnabled`, `oilTemperatureProtectionEnabled`, `fuelTemperatureProtectionEnabled`, `egtProtectionEnabled`, `batteryProtectionEnabled`, `pfiFuelPressureProtectionEnabled`, `gdiRailProtectionEnabled`
- **Proteções unificadas com políticas de aviso e crítico (builds de desenvolvimento)**
  Proteções unificadas oferecem políticas separadas de aviso e crítico, tratamento de falha de sensor, rearme retido e limites de rotação só de combustível para óleo, lambda, boost, duty do injetor, pressão de combustível, temperaturas, EGT e bateria, com controles traduzidos e telemetria de incidentes.
  - Para o preparador
- **Limite final opcional do avanço de ignição**
  Um limite final opcional do avanço de ignição, desligado por padrão para que mapas antigos mantenham o retardo atual.
  - Mapa: campos novos com valor padrão
  - Campos: `ignitionTimingLimitEnabled`
- **Sensores de temperatura com modo compartilhado**
  CLT, IAT, Aux Temp 1 e 2, óleo, combustível, ambiente e descarga do compressor ganham o "Modo do sensor". Independente é o
  comportamento anterior. Compartilhado serve a um sensor ligado a outra ECU: você informa uma curva tensão x temperatura de
  até 8 pontos e a conversão não para mais em 4,9 V. A maior tensão que a entrada lê continua definida pelo divisor da
  placa. Use uma entrada Analog Volt no modo compartilhado.
  - Mapa: campos novos com valor padrão
  - Campos: `cltSharedMode`, `iatSharedMode`, `auxTemp1SharedMode`, `auxTemp2SharedMode`, `oilTempSharedMode`, `fuelTempSharedMode`, `ambientTempSharedMode`, `compressorDischargeTempSharedMode`
- **STFT: diagnósticos de constante de tempo, atraso e pausa**
  Novos mostradores: constante de tempo efetiva, o que a limita (base, transporte do escape, sensor, ciclo ou vazão
  desconhecida), atraso modelado, tempo de pausa restante, idade e taxa de atualização do lambda e os termos P e de
  memória.
  - Para o preparador
- **STFT com PI programado e Smith+PI (somente builds de desenvolvimento)**
  Controladores opcionais "PI programado" e "preditor de Smith" no diálogo da STFT. Desligados por padrão; o integrador
  atual não muda e builds estáveis o mantêm. Os laços novos corrigem um erro de lambda em cerca de um segundo em
  cruzeiro, ignoram a constante de tempo base, aprendem cada erro na célula da grade onde ele começou e mantêm os limites
  de +-25% e as pausas de DFCO, aceleração e corte. O atraso modelado não tem mais piso de 0,2 s (a robustez vem de uma
  constante de tempo mínima de 0,9 s) e a temperatura do gás de escape segue carga e rotação (420 K em marcha lenta até
  1000 K em carga plena), o que alonga o atraso modelado em marcha lenta. Ainda não confirmado em log de veículo.
  - Para o preparador

## Melhorias

- **Curvas de rotação e CLT do enriquecimento multiplicadas de forma contínua**
  As curvas de rotação e de CLT do enriquecimento de aceleração são multiplicadas de forma contínua (um produto
  pequeno não salta mais para 1,0) e, em mapas novos, escalam só a parte de aceleração: o empobrecimento de
  desaceleração é o valor da tabela (antes um motor frio dobrava).
  - Mapa: revisar no seu mapa
  - Campos: `tpsDecelUsesCltRpmMult`
  - O que fazer: Confira o empobrecimento de desaceleração com o motor frio.
- **Enriquecimento de aceleração: lookback 0 desliga cada lado e pico travado por transiente**
  Um lookback igual a 0 desliga o lado correspondente do enriquecimento de aceleração (aceleração ou desaceleração). O
  pico do enriquecimento fica travado por transiente, as médias móveis e o histórico são preparados depois de um reset e
  o filme de parede evapora quando o modelo é desligado. Os menus de Accel Enrichment e Wall Wetting foram reorganizados.
  - Mapa: revisar no seu mapa
  - O que fazer: Confira os lookbacks de aceleração e desaceleração: 0 agora desliga aquele lado.
- **Enriquecimento por TPS projeta a posição da borboleta pela taxa real**
  A consulta inicial da tabela e o tempo de decaimento acompanham a velocidade do pedal: o enriquecimento projeta a
  posição final da borboleta a partir da taxa real do tip-in (antes o piso de 7,5% quase sempre vencia).
- **Tabela TPS/TPS limitada por modo e com unidade na tela**
  A tabela de enriquecimento TPS/TPS é limitada por modo em tempo de execução: pulso fixo aceita até 50 ms por ciclo e
  modo proporcional até uma fração de 2,0 do combustível base (+200%). No modo proporcional a tabela é fração, não
  milissegundos: a tabela de fábrica (em ms) usada como fração somaria +1000% ou mais. O diálogo mostra a unidade do
  modo ativo e um aviso quando uma célula passa do limite; uma tabela salva nunca é reescrita. A dica da tabela informa a
  orientação (x = TPS antes, y = TPS depois) e que a metade de desaceleração sempre empobrece; a tabela de fábrica
  tem zeros ali, então não há empobrecimento na desaceleração até preenchê-la.
  - Mapa: revisar no seu mapa
  - Campos: `tpsTpsAccelTable`
  - O que fazer: Confira a tabela TPS/TPS no modo escolhido: no modo proporcional os valores são fração do combustível base.
- **Enriquecimento por TPS: taxa em % por segundo reais**
  A taxa do TPS passa a ser em porcentagem por segundo reais (antes lia 10 vezes menos que o rótulo). O limiar
  de taxa e o eixo da curva de taxa de um mapa salvo são convertidos uma vez no carregamento (x10), mantendo a
  taxa real de disparo e a posição na curva. De fábrica o limiar é 50 %/s (era 5) e o eixo vai de -1000 a 6000
  (era -100 a 600).
  - Mapa: convertido automaticamente
  - Campos: `tpsAccelEnrichmentThreshold`, `tpsAccelRateBins`, `tpsAccelMinRate`
  - O que fazer: Um arquivo de calibração (.msq) salvo com firmware antiga deve ser convertido à mão: limiar x10 e eixo da taxa x10.
- **evoNet: a ECU transmite os canais pedidos dentro dos limites negociados**
  Os canais pedidos pelo display agora são transmitidos respeitando os limites negociados, e os canais de estado do cruise e de economia e trip são publicados como canais evoNet.
- **Filme de parede: beta sem suavização e limite por ciclo do motor**
  Foi removida a "suavização" que misturava o beta com o alfa quando beta > alfa (degrau de 10% sem estado, com
  salto em beta = alfa). O filme discreto é estável para qualquer beta até o teto de 0,70. O limite de variação
  agora é 5% por ciclo do motor (antes 5% a cada 5 ms, 10 por segundo, quase nunca limitava), vale igual nos modelos
  básico e avançado e recomeça do valor atual depois da partida ou quando o modelo estava desligado. O beta do
  modelo básico também é limitado a 0,70 e reportado assim.
  - Mapa: revisar no seu mapa
  - O que fazer: Revise o enriquecimento de aceleração e o filme de parede em tip-in e tip-out.
- **Tabelas tau e beta do filme usam a carga de combustível como eixo**
  As tabelas de tau e beta do filme de parede usam a carga de combustível como eixo das linhas (kPa em speed density,
  TPS % em alpha-N, enchimento do cilindro % em MAF), como o cursor da tabela já mostrava, e não precisam mais de sensor
  MAP. Carros alpha-N e MAF sem MAP agora aplicam as colunas de rotação (antes a tabela era ignorada): preencha com 1,0
  para manter o comportamento antigo.
  - Mapa: revisar no seu mapa
  - Campos: `wwCorrectionMapBins`
  - O que fazer: Revise mapas alpha-N ou MAF calibrados contra o MAP: o eixo deixou de ser o MAP.
- **Tabelas do filme mostram e editam os eixos que a ECU realmente usa**
  Os eixos mostrados antes não tinham efeito. Um mapa que editou os eixos antigos de MAP e rotação é migrado no
  carregamento (os eixos editados passam a ser os usados), então o combustível transiente desse mapa muda; mapas de
  fábrica não mudam. O Burn é recusado quando esses eixos não são crescentes. As curvas 1D "Tempo de evaporação x MAP" e
  "Fração de impacto x MAP", que nunca foram lidas, saíram do tuner.
  - Mapa: convertido automaticamente
  - Campos: `wwTauMapValues`, `wwBetaMapValues`
  - O que fazer: Revise o combustível transiente de um mapa que tenha editado os eixos antigos do filme.
- **Novos canais firmwareBuildId e configLayoutVersion para identificar o build exato**
  A ECU passa a publicar, no fim dos canais de saída, o identificador do commit do build
  (firmwareBuildId, 8 primeiros dígitos hexadecimais) e a versão do layout da configuração
  (configLayoutVersion). Com isso o Manager identifica o build instalado mesmo quando a
  assinatura é igual e confere o layout real da memória. Nenhum canal existente muda de
  posição e a assinatura mantém o formato.
  - Para o preparador
- **Recuperação do duty do injetor configurável**
  O percentual de recuperação do duty do injetor é configurável (padrão 20%, sem exigência de pedal ou TPS) e a visão geral
  lista as regras de proteção ativas. O duty do injetor mostra "aguardando" com o motor parado e "cálculo indisponível"
  quando o cálculo em funcionamento é inválido, em vez de citar um sensor de duty que não existe.
  - Mapa: revisar no seu mapa
  - Campos: `epDutyRecoveryThreshold`
  - O que fazer: Revise o percentual de recuperação do duty do injetor ao atualizar.
- **Largada e corte na troca não atuam juntos**
  Com os dois ligados e a velocidade conhecida, a largada (launch) atua só abaixo da "velocidade máxima de largada" (0 vale
  30 km/h) e o corte na troca só acima dela mais uma faixa fixa de 5 km/h, com histerese. Com o mesmo botão ou embreagem nos
  dois, a velocidade decide quando há sensor funcionando; sem ele (ou com falha) vale a divisão por rotação, que agora também
  cobre embreagem compartilhada. Um carro parado com sensor de velocidade por pulsos conta como parado. Largada ou corte na
  troca sozinhos se comportam como antes. A regra de velocidade está sempre ligada, sem ajuste.
  - Mapa: revisar no seu mapa
  - Campos: `launchTpsThreshold`
  - O que fazer: Confira o campo de pedal da largada: agora é 'PPS/TPS mínimo para largar' em % (de 0 a 100) e não mais um limite máximo.
- **Corte na troca em um só menu, com painel de status**
  Menu único "Desempenho > Corte na Troca (Flat Shift)" com o gatilho, as condições, a duração, as três tabelas e um painel
  de status que mostra qual condição bloqueia o corte. Os campos "Limitar duração do corte" e o modo do botão voltam a ser
  editáveis, as tabelas ficam sempre visíveis e mostram a célula ativa, e o campo de pedal se chama PPS/TPS. A tabela de
  ponto de ignição do corte é um avanço absoluto (substitui a tabela principal), como o rótulo e a ajuda agora dizem.
  - Mapa: revisar no seu mapa
  - Campos: `torqueReductionArmingApp`, `torqueReductionTimeTable`
  - O que fazer: Confira o pedal de armar (% de 0 a 100) e as tabelas de duração do corte na nova tela.
- **Espectro de detonação calibrado em dBV e FFT do tamanho da janela capturada**
  As amplitudes do espectro são dBV calibrados (-100 a +27,5 dBV em passos de 0,5 dB), em vez do valor 0-255 não calibrado
  que saturava depois de cerca de 12 dB. Mostradores ou logs que leem esses canais precisam ser reinterpretados. A FFT
  se dimensiona pela janela realmente capturada: acima de cerca de 3200 rpm informa menos faixas e mais largas, em vez de
  uma curva mais fina do que os dados sustentam. Use "Tamanho fixo da FFT" para um eixo estável ao comparar capturas. A
  "Sensibilidade do espectro de detonação" não afeta mais o espectro reportado, e o espectro informa quantas faixas são
  válidas, a resolução real em Hz e quantas janelas a ECU precisou pular.
  - Mapa: campos novos com valor padrão
  - Campos: `knockSpectrumFixedSize`
  - Para o preparador
- **A configuração da ECU é apagada na primeira partida (layout 261027)**
  Quatro mudanças de layout da configuração desde a versão estável de 07/09/2026 (proteções unificadas,
  histórico de proteções, curvas de sensores de temperatura compartilhados e PWM senoidal da marcha lenta)
  levam a configuração da ECU de 260821 para 261027. Ao partir pela primeira vez com esta versão, a ECU
  descarta o mapa salvo e volta ao padrão de fábrica. É preciso usar o INI desta mesma versão.
  - Mapa: APAGA a configuração da ECU
  - O que fazer: Exporte o mapa (.msq) antes de atualizar. Na primeira partida com esta versão a ECU apaga a configuração salva; depois, importe o mapa e revise os itens marcados como revisar.
- **MAF: modelo de enchimento do coletor, sempre ativo**
  O ar do cilindro passa a ser a vazão do MAF atrasada por um filtro de 1ª ordem, com constante de tempo
  120 x volume / (VE de referência x cilindrada x rotação). O ar modelado alimenta o combustível, a carga e os eixos
  das tabelas de VE, AFR e ignição, e a vazão de escape da STFT; em regime nada muda e, em tip-in e tip-out, o pico de
  carga do MAF deixa de ser tratado como ar do cilindro. Padrão de 2,0 L em Sensores > MAF > MAF Sensor
  ("Effective manifold volume", 0 a 10 L); 0 L reproduz exatamente o comportamento anterior. Canais novos no log:
  mafCylFlowEstimate, mafManifoldTauMs, mafManifoldState, cylinderAirmassRaw e fuelingLoadRaw.
  - Mapa: campos novos com valor padrão
  - Campos: `mafManifoldVolumeL`, `mafManifoldTauScale`, `mafManifoldTauMaxMs`, `mafManifoldEtaV`, `mafManifoldLeadMs`
  - O que fazer: Enriquecimento de aceleração e filme de parede calibrados com o MAF bruto podem precisar de ajuste.
- **A marca evoTech aparece no lugar de rusEFI nas telas do usuário**
  Textos voltados ao usuário passam a apresentar evoTech em vez de rusEFI. A assinatura do INI ('rusEFI <branch>.<data>.<placa>.<hash>') não muda de formato.
- **Proteções do motor com um supervisor único**
  Óleo, lambda, boost e duty do injetor (e depois pressão de combustível, temperaturas, EGT e bateria) usam um único
  supervisor de proteções, com políticas separadas de aviso e crítico, tratamento de falha de sensor, rearme retido e
  limites de rotação só de combustível; o seletor legado saiu. As proteções se recuperam sozinhas quando as condições de
  recuperação são atendidas, sem reconhecimento do Manager; a recuperação do óleo na partida e do prazo da bobina exige
  motor parado estável. Extensões avançadas continuam só em builds de desenvolvimento.
  - Mapa: revisar no seu mapa
  - Campos: `protectionConfigVersion`, `epOilLow_mode`, `epLambda_mode`, `epBoost_mode`, `epDuty_mode`
  - O que fazer: Revise os limites e a recuperação de todas as proteções ao atualizar.
- **Sensores em entrada Analog Temp sempre usam o pull-up de 2700 ohm da placa**
  Sensores de temperatura em entrada Analog Temp, no modo independente, sempre usam o pull-up de 2700 ohm da placa e o campo do resistor deixou de aparecer. Sensores em entrada Analog Volt mantêm o valor configurado.
  - Mapa: revisar no seu mapa
  - O que fazer: Confira os sensores de temperatura em entradas Analog Temp: o pull-up é sempre o da placa.
- **STFT com filtro de realimentação próprio, independente do lambda suavizado**
  A STFT usa um filtro de realimentação próprio, baseado em tempo, independente da suavização do lambda mostrado. O
  orçamento de resposta inclui um ciclo do motor e o filtro de controle.
  - Mapa: revisar no seu mapa
  - O que fazer: Revise a resposta do frio ao quente nas calibrações com a STFT ligada.
- **Controle de tração padrão usa aceleração de rotação com sinal e sincronização limitada**
  O modelo padrão usa a aceleração de rotação com sinal e uma sincronização automática limitada na troca de marcha, evitando reter a demanda em rebotes de rotação.

## Correções

- **Enriquecimento e empobrecimento decaem de forma exponencial na cauda inteira**
  O enriquecimento e o empobrecimento de aceleração do TPS decaem de forma exponencial por toda a cauda, em vez de subir
  a um platô artificial de 81,8% depois de duas constantes de tempo. O filme de parede também usa um exponencial válido
  com constantes de evaporação pequenas, e o combustível do DFCO decai de forma monotônica até o piso, sem voltar a
  subir no meio do corte.
  - Mapa: revisar no seu mapa
  - O que fazer: Revise a calibração transiente (aceleração, filme e DFCO) depois de atualizar.
- **Burn perdido depois de atualização que muda o tamanho da configuração**
  O Burn se perdia em silêncio depois de uma atualização que mudava o tamanho da configuração: toda partida reiniciava o mapa com 'version mismatch' e nada persistia. Agora o Burn reconstrói a flash com o motor parado. Depois de instalar esta versão, faça um Burn com o motor parado; o mapa anterior à atualização anterior não pode ser recuperado.
- **Desligar o corte na troca limpa o estado na hora**
  Ao desligar o corte na troca, os indicadores e a camada de prioridade da suavização de torque deixam de manter o último valor.
- **Cruise control: RESUME volta a funcionar depois do freio ou de um CANCEL**
  O RESUME agora funciona depois que a suspensão por freio ou embreagem termina e depois de um CANCEL (só era aceito com o pedal ainda pressionado). A velocidade alvo salva é restaurada se o veículo estiver acima da velocidade mínima de retomada.
- **ECU virgem não acusa mais 'Flash consolidation produced a CRC mismatch'**
  Uma ECU virgem (ou com configuração salva incompatível) deixa de gerar o erro logo após o boot: a flash só é consolidada depois que tem uma configuração válida, após o primeiro Burn.
- **Guarda de embreagem compara rotação do motor com a do cardã nas mesmas unidades**
  A discordância de relação da proteção de embreagem passa a comparar a rotação do motor com a rotação da transmissão em unidades coerentes.
- **Autotune do PID da ETB não fica mais armado**
  O autotune se encerra sozinho após 30 segundos, quando o motor gira ou quando a ignição desliga, e o botão
  Parar fica habilitado enquanto ele está ativo (antes só funcionava com uma oscilação em andamento). Uma
  calibração automática com pouco curso da borboleta não gera mais erro crítico: informa "curso pequeno" e
  deixa a ECU funcionando. A calibração automática também recusa rodar com o controle do motor da ETB pausado.
- **evoNet: canais de cruise e economia/trip passam a ser publicados como válidos**
  Os canais evoNet de cruise (estado, alvo, esforço, motivo de desligamento) e de trip e economia (distância, combustível,
  economia instantânea e média) nunca eram publicados como válidos: a tabela do datalogger ignorava as saídas dos módulos
  de live data, e o display via "aguardando" para sempre. Agora transmitem normalmente.
- **evoNet não relata mais falhas obsoletas do controlador da ETB**
  Depois que a saída é desabilitada ou atribuída a outra função, o evoNet deixa de informar falhas antigas da ETB; falhas retidas reais continuam visíveis. A pilha de transmissão CAN também foi aumentada para impedir reinícios da ECU causados por alertas evoNet.
- **Limites do TPS em volts com a escala real e ETB 2 corrigida**
  Os limites de calibração do TPS aparecem em volts com a escala real (0,005 V por contagem, 200 contagens por
  volt) nas duas borboletas. Antes o TPS 1 lia 2,4% a menos (cerca de 97% com a borboleta toda aberta depois de
  calibrar pelo TunerStudio) e os limites da ETB 2 eram gravados como números crus, e calibrar a ETB 2 pelo botão
  gerava valores que faziam a partida seguinte falhar com "cal values are too close together".
  - Mapa: revisar no seu mapa
  - Campos: `tpsMin`, `tpsMax`, `tps1SecondaryMin`, `tps1SecondaryMax`, `tps2Min`, `tps2Max`, `tps2SecondaryMin`, `tps2SecondaryMax`
  - O que fazer: Recalibre o TPS 1 e a ETB 2 depois de atualizar.
- **Espectro de detonação não analisa mais amostras que nunca foram capturadas**
  Acima de cerca de 1600 rpm a análise completava a janela com sobras da captura anterior, possivelmente de outro cilindro e sensor, e gerava um espectro misturando duas janelas. Uma calibração com o espectrograma ligado também não impede mais a ECU de partir em placas sem o recurso: a opção é desligada com um aviso.
  - Para o preparador
- **LTFT não aprende uma correção travada da STFT**
  O LTFT deixa de aprender uma correção da STFT mantida enquanto o banco está pausado por disponibilidade do lambda, DFCO, aceleração ou corte recente. Valores de lambda inválidos não entram mais no aprendizado da STFT.
- **Frequência da solenoide de marcha lenta vale sem reiniciar**
  Mudanças na frequência da solenoide de marcha lenta valem sem reiniciar a ECU e preservam o duty comandado.
  Reconfigurar saídas de válvula para o PWM antigo com segurança e ajustes externos de PWM por GPIO não consomem outro
  canal para o mesmo pino.
  - Mapa: revisar no seu mapa
  - Campos: `idle_solenoidFrequency`
  - O que fazer: A frequência agora vai de 1 a 3000 Hz (0 deixou de ser aceito): confira o valor.
- **Osciloscópio preserva bordas reais e reporta falha de alocação**
  O osciloscópio preserva bordas reais de virabrequim e comando e as saídas de ignição individuais, reinicia com segurança o conjunto de buffers e informa falhas de alocação da captura em vez de confirmar uma captura inativa.
  - Para o preparador
- **Robustez da ETB, do ADC rápido e dos chips SPI inteligentes**
  A trava de falha da ETB é liberada por um novo ciclo de ignição e o limitador de rotação sempre volta; os contadores de
  erro intermitente do sensor da ETB decaem em vez de acumular durante todo o ciclo de ignição; o ADC rápido é reiniciado
  depois de um erro de DMA ou overrun; chips SPI inteligentes contam falhas consecutivas, publicam smartChipState e se
  reinicializam; o callback rápido não é reentrado pelo tratador do gatilho; e há proteções contra temperatura de carga zero,
  ângulo de dwell com o motor parado, aplicação da configuração na janela de boot e contador de quedas do EXTI, entre outros achados da análise de robustez.
- **Calibração de sensor de temperatura imperfeita não derruba mais a ECU**
  Uma calibração que não é um ajuste perfeito (por exemplo um sensor compartilhado com outra ECU) deixa de desligar a ECU com erro crítico. O sensor é marcado como mal configurado com um aviso, a última calibração válida é mantida enquanto você edita os pontos e o motor continua funcionando. A curva de CLT padrão também não gera mais o aviso 'curve fit is poor' em toda partida.
- **STFT: atraso de transporte do escape não depende mais do MAP**
  Num carro alpha-N sem MAP o modelo informava vazão desconhecida o tempo todo, o que prendia o atraso em 2 s e a
  constante de tempo da correção perto de 4,7 s, qualquer que fosse a constante base (e deixava o Smith com atraso
  errado). A vazão agora vem da massa de ar do cilindro que a estratégia de combustível já calcula (alpha-N, speed
  density e MAF). "Vazão inválida" só aparece enquanto essa massa de ar não está disponível. Ainda não confirmado em log
  de veículo.
- **Estado da STFT no tuner não é mais truncado**
  O estado da STFT mostrado no tuner era truncado nas pausas de aceleração (8) e de corte de combustível (9); o campo agora tem 4 bits.
  - Para o preparador
- **STFT pausado durante todo o enriquecimento de aceleração**
  A correção em malha fechada (STFT) fica pausada durante toda a aceleração ou desaceleração, incluindo a cauda
  exponencial, mais o tempo configurado depois (antes contava do início do transiente e podia voltar com o enriquecimento
  ainda ativo). Tempo igual a 0 continua desligando a pausa. O sensor de flex virtual também ignora o aprendizado durante
  um enriquecimento de aceleração ou desaceleração, em qualquer modo.
- **Controle de tração limpa o retardo e o corte residuais**
  O controle de tração limpa o retardo de ignição e o corte de faísca residuais ao desligar, com a embreagem aberta e com
  callback ou rotação inválidos, mantém o filtro de rotação atualizado nas portas de pedal e MAP, rejeita curvas inválidas,
  recupera o controle padrão depois de trocas de marcha e evita um corte falso em trocas sem embreagem com acelerador
  antecipado.
- **Traduções pt-BR de avanço máximo/mínimo, largada e embreagem**
  "Maximum/Minimum timing advance" (Ajustes de ignição) traduzido; o "TPS Threshold" da largada agora é "PPS/TPS mínimo
  para largar" (estava traduzido como máximo); rótulos da entrada de embreagem por extenso; "deg BTDC" aparece como
  "graus APMS".

## Segurança

- **Cruise control suspende ao perder o sensor de velocidade**
  Com o sensor de velocidade do veículo perdido, o cruise control suspende em vez de regular contra uma velocidade congelada.
- **Comandos, pacotes e scripts externos inválidos são rejeitados sem parar o motor**
  Comandos, pacotes e scripts vindos de fora (TunerStudio, CAN, Lua) que antes podiam provocar um erro fatal e parar o
  motor agora são rejeitados. Requisições de página do TunerStudio menores que o cabeçalho e escritas em bloco cuja
  contagem excede o pacote também. A rota CAN sem autenticação que executava comandos arbitrários do TunerStudio foi
  removida. As escritas em bloco do TunerStudio preservam o odômetro, os trims aprendidos, o etanol estimado e o histórico de
  proteções.
- **Configuração inválida é rejeitada no Burn em vez de gerar erro fatal ou pulso infinito**
  Todos os eixos de tabela são validados na partida e no Burn, e um eixo ou limite inválido rejeita a configuração em vez de
  gerar erro fatal. Configurações com divisores zero, ordem de ignição ou sincronismo GDI inválidos são recusadas pelo Burn.
  Vazão zero ou lambda alvo zero não geram mais pulso de injeção infinito. Uma regra de proteção malformada só corta
  combustível depois de 500 ms, então uma edição ao vivo não vira corte.

## Removido

- **Correção de avanço pela tabela TPS/TPS removida**
  A tabela de correção de ignição TPS/TPS (habilitação, eixos de origem e destino e tabela) foi removida junto com a reorganização dos menus de enriquecimento de aceleração e filme de parede; o layout foi preservado em campos reservados.
  - Mapa: revisar no seu mapa
  - Campos: `tpsTpsTimingCorrectionEnable`, `tpsTpsTimingCorrFromRpmBins`, `tpsTpsTimingCorrToRpmBins`, `tpsTpsTimingCorrectionTable`
  - O que fazer: Se você usava a correção de avanço pelo TPS/TPS, recalibre o avanço de aceleração pelas tabelas de ignição.
- **Protocolo do logger de alta velocidade substituído**
  O protocolo novo do logger de alta velocidade substituiu o formato antigo composto/tooth logger. O TunerStudio e outras ferramentas que leem o formato antigo deixam de recebê-lo.
  - Mapa: revisar no seu mapa
  - O que fazer: Atualize ferramentas que liam o logger de dentes antigo.
  - Para o preparador
- **STFT: controlador normal/legado e passo fixo removidos**
  A STFT sempre usa PI, com a compensação de atraso de Smith ligada por padrão e desligável de forma independente. Mapas
  existentes adotam PI + Smith sem ligar a correção em malha fechada que estiver desligada globalmente. A constante de
  tempo de referência passa a aparecer só nas configurações de aprendizado do LTFT.
  - Mapa: revisar no seu mapa
  - Campos: `stftIgnoreErrorMagnitude`, `disableStftSmithPredictor`
  - O que fazer: Revise a resposta da STFT (do frio ao quente) e o uso do preditor de Smith; o modo normal/legado saiu.

Versão do layout da configuração: 261027
