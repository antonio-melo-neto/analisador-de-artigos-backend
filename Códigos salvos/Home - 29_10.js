import React, { useState, useEffect } from 'react';
import { Button, Container, TextField, Table, TableHead, TableRow, TableCell, TableBody } from '@mui/material';
import { ArrowDownward } from '@mui/icons-material';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import api from '../services/api';
import '../styles.css';
import '../tabela2.css';

function Home() {
  const [file, setFile] = useState(null);
  const [data, setData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [anos, setAnos] = useState({ anoInicio: '', anoFim: '' });
  const [nomePessoa, setNomePessoa] = useState('');
  const [pontuacaoQualis, setPontuacaoQualis] = useState([]);
  const [ponderacaoDiscente, setPonderacaoDiscente] = useState(75);
  const [editableData, setEditableData] = useState([]);
  const [savedData, setSavedData] = useState(() => {
    const saved = localStorage.getItem('savedData');
    return saved ? JSON.parse(saved) : [];
  });

const [uploading, setUploading] = useState(false); // Indica se estamos realizando upload
  
const handleUpload = async () => {
    if (!file) return alert('Selecione o arquivo XML!');
    
    // Resetar os estados ao iniciar um novo upload e limpar o localStorage
    setUploading(true);
    setSavedData([]);
    setEditableData([]);
    setData([]); // Limpa o estado dos dados principais
    localStorage.removeItem('savedData'); // Remove savedData do localStorage

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await api.post('/upload/', formData);
        const { nomePessoa, artigos, pontuacaoQualis } = response.data;
        setNomePessoa(nomePessoa);

        // Ajustar os dados recebidos
        const adjustedData = artigos.map((item) => ({
            ...item,
            Qualis: item.Qualis || 'NP',
            '2023 JIF': item['2023 JIF'] || '---',
            'JIF Quartile': item['JIF Quartile'] || '---',
            SJR: item.SJR || '---',
            'SJR Best Quartile': item['SJR Best Quartile'] || '---',
            DOI: `http://dx.doi.org/${item.DOI}`,
        }));

        setData(adjustedData); // Definir data com os dados ajustados
        setEditableData(adjustedData); // Definir o estado editável com os novos dados
        setPontuacaoQualis(pontuacaoQualis);

        aplicarFiltroAnos(); // Reaplica o filtro de anos imediatamente após o upload

        setFile(null); // Limpa o input de arquivo para permitir novo upload
        alert('Arquivo enviado com sucesso!');
    } catch (error) {
        console.error('Erro ao enviar o arquivo:', error);
        alert('Erro ao enviar o arquivo.');
    } finally {
        setUploading(false); // Conclui o upload
    }
};

// Função para aplicar o filtro de anos nos dados
const aplicarFiltroAnos = () => {
    let dadosFiltrados = data;
    if (anos.anoInicio && anos.anoFim) {
      dadosFiltrados = data.filter(
        (item) => item.Ano >= parseInt(anos.anoInicio) && item.Ano <= parseInt(anos.anoFim)
      );
    }
    setEditableData(dadosFiltrados); // Atualiza o `editableData` após o filtro
};

// useEffect para reaplicar o filtro quando os anos ou dados principais mudam
useEffect(() => {
    aplicarFiltroAnos();
}, [anos, data]);

// useEffect para restaurar savedData se não estivermos fazendo upload
useEffect(() => {
    if (!uploading) {
        if (savedData.length > 0) {
            setEditableData(savedData);
        } else {
            aplicarFiltroAnos(); // Garante que o filtro seja reaplicado
        }
    }
}, [savedData, uploading]);

  const atualizarTabelas = () => {
    const updatedData = editableData.map((item) => ({
      ...item,
      Pts: calcularPontuacao(item.Qualis, item.DP, item.DIS, ponderacaoDiscente),
    }));

    setFilteredData(updatedData);
    recalcularTabela2(updatedData);
  };

  useEffect(() => {
    atualizarTabelas();
  }, [editableData, ponderacaoDiscente]);

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
  };

  const handleSaveEdit = () => {
    setSavedData([...editableData]);
    localStorage.setItem('savedData', JSON.stringify(editableData));
    alert('Edição salva com sucesso!');
  };

  const handleResetEdit = () => {
    if (savedData.length > 0) {
      setEditableData([...savedData]);
      alert('Edição restaurada para o último salvamento.');
    } else {
      alert('Nenhuma edição salva para restaurar.');
    }
  };

  const handleAnoChange = (e) =>
    setAnos((prev) => ({ ...prev, [e.target.name]: e.target.value }));

  const handlePonderacaoChange = (e) => {
    setPonderacaoDiscente(e.target.value);
  };

  const handleInputChange = (e, index, field) => {
    const updatedData = [...editableData];
    const newValue = e.target.value === '' ? 0 : parseInt(e.target.value, 10);
    updatedData[index][field] = isNaN(newValue) ? 0 : newValue;
    setEditableData(updatedData); // Atualiza o estado editável
    atualizarTabelas(); // Recalcula Tabela 1 e Tabela 2 com as edições aplicadas
  };

  const recalcularTabela2 = (data) => {
    const pontuacaoPorAno = {};
    data.forEach((item) => {
      if (!pontuacaoPorAno[item.Ano]) {
        pontuacaoPorAno[item.Ano] = {
          A1: 0,
          A2: 0,
          A3: 0,
          A4: 0,
          B1: 0,
          B2: 0,
          B3: 0,
          B4: 0,
          C: 0,
          NP: 0,
          TotalA: 0,
          TotalB: 0,
          PtsAno: 0,
        };
      }
      pontuacaoPorAno[item.Ano][item.Qualis] += item.Pts;
      if (['A1', 'A2', 'A3', 'A4'].includes(item.Qualis)) {
        pontuacaoPorAno[item.Ano].TotalA += item.Pts;
      } else if (['B1', 'B2', 'B3', 'B4'].includes(item.Qualis)) {
        pontuacaoPorAno[item.Ano].TotalB += item.Pts;
      }
      pontuacaoPorAno[item.Ano].PtsAno += item.Pts;
    });

    Object.keys(pontuacaoPorAno).forEach((ano) => {
      const totalAno = pontuacaoPorAno[ano].PtsAno;
      pontuacaoPorAno[ano]['% A'] =
        totalAno > 0 ? (pontuacaoPorAno[ano].TotalA / totalAno) * 100 : 0;
      pontuacaoPorAno[ano]['% B'] =
        totalAno > 0 ? (pontuacaoPorAno[ano].TotalB / totalAno) * 100 : 0;
    });

    setPontuacaoQualis(
      Object.keys(pontuacaoPorAno).map((ano) => ({
        Ano: ano,
        A1: pontuacaoPorAno[ano].A1,
        A2: pontuacaoPorAno[ano].A2,
        A3: pontuacaoPorAno[ano].A3,
        A4: pontuacaoPorAno[ano].A4,
        B1: pontuacaoPorAno[ano].B1,
        B2: pontuacaoPorAno[ano].B2,
        B3: pontuacaoPorAno[ano].B3,
        B4: pontuacaoPorAno[ano].B4,
        C: pontuacaoPorAno[ano].C,
        NP: pontuacaoPorAno[ano].NP,
        TotalA: pontuacaoPorAno[ano].TotalA,
        TotalB: pontuacaoPorAno[ano].TotalB,
        '% A': pontuacaoPorAno[ano]['% A'],
        '% B': pontuacaoPorAno[ano]['% B'],
      }))
    );
  };

  const calcularPontuacao = (qualis, dp, dis, ponderacaoDiscente) => {
    const qualisPts = {
      A1: 1,
      A2: 0.9,
      A3: 0.75,
      A4: 0.6,
      B1: 0.4,
      B2: 0.3,
      B3: 0.15,
      B4: 0.05,
      C: 0,
    };
    const basePts = qualisPts[qualis] || 0;
    const ponderacao = dis === 0 ? ponderacaoDiscente / 100 : 1;
    return (basePts * ponderacao) / Math.max(dp, 1);
  };

  const generatePDF = () => {
    const input = document.getElementById('pdf-content');

    html2canvas(input, { scale: 2 }).then((canvas) => {
      const imgData = canvas.toDataURL('image/jpeg', 0.9);
      const pdf = new jsPDF('p', 'mm', 'a4');
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      const margin = 10;
      const imgWidth = pageWidth - margin * 2;
      const imgHeight = (canvas.height * imgWidth) / canvas.width;
      let position = margin;

      if (imgHeight > pageHeight - margin * 2) {
        let remainingHeight = imgHeight;

        while (remainingHeight > 0) {
          pdf.addImage(
            imgData,
            'JPEG',
            margin,
            position,
            imgWidth,
            Math.min(remainingHeight, pageHeight - margin * 2)
          );
          remainingHeight -= pageHeight - margin * 2;
          if (remainingHeight > 0) {
            pdf.addPage();
            position = margin;
          }
        }
      } else {
        pdf.addImage(imgData, 'JPEG', margin, margin, imgWidth, imgHeight);
      }

      const nomeDocente = nomePessoa || 'Relatório';
      pdf.save(`${nomeDocente} - Relatório de Pontuação PPGEC.pdf`);
    });
  };

  return (
    <Container
      className="container-ppgec"
      maxWidth={false}
      style={{ paddingLeft: 70, paddingRight: 70, maxWidth: '1600px', margin: '0 auto' }}
    >
      <div id="pdf-content">
        <div className="logo-container">
          <img
            src={require('../assets/PPGEC Tipo 2.png')}
            alt="Logo PPGEC"
            className="ppgec-logo"
          />
          <h1 className="ppgec-title">Programa de Pós-graduação em Engenharia Civil</h1>
          <h2 className="ppgec-subtitle">Analisador de Artigos</h2>
        </div>
        {nomePessoa && <h2 className="nome-pessoa">{nomePessoa}</h2>}

        <div className="anos-container">
          <TextField
            label="Ano - Início"
            name="anoInicio"
            type="number"
            value={anos.anoInicio}
            onChange={handleAnoChange}
            variant="outlined"
            style={{
              fontSize: 12,
              fontWeight: 'bold',
              height: 60,
              width: 100,
              textAlign: 'center',
            }}
          />
          <TextField
            label="Ano - Fim"
            name="anoFim"
            type="number"
            value={anos.anoFim}
            onChange={handleAnoChange}
            variant="outlined"
            style={{
              fontSize: 12,
              fontWeight: 'bold',
              height: 60,
              width: 100,
              textAlign: 'center',
            }}
          />
          <TextField
            label="Ponderação Discente (%)"
            type="number"
            value={ponderacaoDiscente}
            onChange={handlePonderacaoChange}
            variant="outlined"
            style={{
              fontSize: 12,
              fontWeight: 'bold',
              height: 60,
              width: 170,
              textAlign: 'center',
            }}
          />
          <div className="upload-container">
            <div className="upload-label">
              <label>Lattes (XML .zip)</label>
              <input type="file" name="file" onChange={handleFileChange} className="file-input" />
            </div>
            <Button
              variant="contained"
              color="primary"
              onClick={handleUpload}
              className="upload-button"
              style={{ marginLeft: '10px', height: '40px' }}
            >
              Enviar XML
            </Button>
          </div>
        </div>

        {/* Tabela 1 */}
        <h2 className="table-title">Tabela 1 - Listagem de artigos</h2>
        {filteredData.length > 0 && (
          <Table className="custom-table">
            <TableHead>
              <TableRow className="table-header">
                {[
                  'Ano', 'DOI', 'ISSN', 'Periódico', 'Título', 'Autores', 'Qualis', 'JCR', 'Quartil', 'SJR',
                  'Quartil2', 'DP', 'DC', 'DIS', 'Pts'
                ].map((header) => (
                  <TableCell key={header} className={`col-${header.toLowerCase().replace(' ', '-')}`}>
                    {header === 'Quartil' ? (
                      <>Q<sub>jcr</sub></>
                    ) : header === 'Quartil2' ? (
                      <>Q<sub>sjr</sub></>
                    ) : (
                      header
                    )}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredData.map((item, index) => (
                <TableRow key={index} className={index % 2 === 0 ? 'even-row' : 'odd-row'}>
                  <TableCell className="col-ano">{item.Ano}</TableCell>
                  <TableCell className="col-doi">
                    <a href={item.DOI} target="_blank" rel="noopener noreferrer">
                      <ArrowDownward style={{ color: 'rgb(40, 161, 219)' }} />
                    </a>
                  </TableCell>
                  <TableCell className="col-issn">{item.ISSN}</TableCell>
                  <TableCell className="col-periodico">{item['Título do Periódico']}</TableCell>
                  <TableCell className="col-titulo">{item.Título}</TableCell>
                  <TableCell className="col-autores">{item.Autores}</TableCell>
                  <TableCell className="col-qualis">{item.Qualis}</TableCell>
                  <TableCell className="col-jcr">{item['2023 JIF']}</TableCell>
                  <TableCell className="col-quartil-jcr">{item['JIF Quartile']}</TableCell>
                  <TableCell className="col-sjr">
                    {item.SJR && !isNaN(parseFloat(item.SJR.replace(',', '.').trim()))
                      ? parseFloat(item.SJR.replace(',', '.').trim()).toLocaleString('pt-BR', {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })
                      : '---'}
                  </TableCell>
                  <TableCell className="col-quartil-sjr">{item['SJR Best Quartile']}</TableCell>
                  <TableCell className="col-dp" align="center">
                    <input
                      type="text"
                      value={item.DP}
                      onChange={(e) => handleInputChange(e, index, 'DP')}
                      className="input-editable"
                    />
                  </TableCell>
                  <TableCell className="col-dc" align="center">
                    <input
                      type="text"
                      value={item.DC}
                      onChange={(e) => handleInputChange(e, index, 'DC')}
                      className="input-editable"
                    />
                  </TableCell>
                  <TableCell className="col-dis" align="center">
                    <input
                      type="text"
                      value={item.DIS}
                      onChange={(e) => handleInputChange(e, index, 'DIS')}
                      className="input-editable"
                    />
                  </TableCell>
                  <TableCell className="col-pts">
                    {calcularPontuacao(item.Qualis, item.DP, item.DIS, ponderacaoDiscente).toLocaleString('pt-BR', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}

        {/* Tabela 2 - Pontuação Qualis */}
        <h2 className="table-qualis-title">Tabela 2 - Pontuação Qualis</h2>
        <div className="tabela-e-pontuacao">
          <div className="tabela2-container">
            <Table className="table-qualis">
              <TableHead>
                <TableRow className="table-header">
                  <TableCell className="col-ano">Ano</TableCell>
                  <TableCell className="col-a1">A1</TableCell>
                  <TableCell className="col-a2">A2</TableCell>
                  <TableCell className="col-a3">A3</TableCell>
                  <TableCell className="col-a4">A4</TableCell>
                  <TableCell className="col-b1">B1</TableCell>
                  <TableCell className="col-b2">B2</TableCell>
                  <TableCell className="col-b3">B3</TableCell>
                  <TableCell className="col-b4">B4</TableCell>
                  <TableCell className="col-c">C</TableCell>
                  <TableCell className="col-np">NP</TableCell>
                  <TableCell className="col-percent-b">% B</TableCell>
                  <TableCell className="col-total-b">Total B</TableCell>
                  <TableCell className="col-percent-a">% A</TableCell>
                  <TableCell className="col-pqd1-a">PQD1_A</TableCell>
                  <TableCell className="col-pqd1">PQD1</TableCell>
                  <TableCell className="col-pqd1-ab">PQD1_AB</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {pontuacaoQualis.map((row, index) => {
                  const a1 = row.A1 || 0;
                  const a2 = row.A2 || 0;
                  const a3 = row.A3 || 0;
                  const a4 = row.A4 || 0;
                  const b1 = row.B1 || 0;
                  const b2 = row.B2 || 0;
                  const b3 = row.B3 || 0;
                  const b4 = row.B4 || 0;
                  const totalA = a1 + a2 + a3 + a4;
                  const totalB = b1 + b2 + b3 + b4;
                  const pqd1_ab = totalA + totalB;
                  const pqd1 = pqd1_ab + 0.2 * totalA;
                  const percentA = pqd1_ab > 0 ? (totalA / pqd1_ab) * 100 : 0;
                  const percentB = pqd1_ab > 0 ? (totalB / pqd1_ab) * 100 : 0;

                  return (
                    <TableRow key={index} className={index % 2 === 0 ? 'even-row' : 'odd-row'}>
                      <TableCell className="col-ano">{row.Ano}</TableCell>
                      <TableCell className="col-a1">
                        {a1.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </TableCell>
                      <TableCell className="col-a2">
                        {a2.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </TableCell>
                      <TableCell className="col-a3">
                        {a3.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </TableCell>
                      <TableCell className="col-a4">
                        {a4.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </TableCell>
                      <TableCell className="col-b1">
                        {b1.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </TableCell>
                      <TableCell className="col-b2">
                        {b2.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </TableCell>
                      <TableCell className="col-b3">
                        {b3.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </TableCell>
                      <TableCell className="col-b4">
                        {b4.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </TableCell>
                      <TableCell className="col-c">
                        {(row.C || 0).toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                      </TableCell>
                      <TableCell className="col-np">
                        {(row.NP || 0).toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                      </TableCell>
                      <TableCell className="col-percent-b">
                        {percentB.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
                      </TableCell>
                      <TableCell className="col-total-b">
                        {totalB.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </TableCell>
                      <TableCell className="col-percent-a">
                        {percentA.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
                      </TableCell>
                      <TableCell className="col-pqd1-a">
                        {totalA.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </TableCell>
                      <TableCell className="col-pqd1">
                        {pqd1.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </TableCell>
                      <TableCell className="col-pqd1-ab">
                        {pqd1_ab.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>

          {/* Caixa de Pontuação */}
          <div className="pontuacao-container">
            <h3>Pontuação</h3>
            <p className="pontuacao-value">
              {pontuacaoQualis.reduce((acc, row) => acc + (row.TotalA || 0) + (row.TotalB || 0), 0).toLocaleString(
                'pt-BR',
                { minimumFractionDigits: 2, maximumFractionDigits: 2 }
              )}
            </p>
          </div>
        </div>

        {/* Botões de Ação - abaixo de tudo */}
        <div className="action-buttons">
          <Button
            variant="contained"
            color="primary"
            onClick={generatePDF}
            className="generate-pdf-button"
          >
            Gerar PDF
          </Button>
          <Button
            variant="contained"
            color="primary"
            onClick={handleSaveEdit}
            className="save-edit-button"
            style={{ marginLeft: '10px' }}
          >
            Salvar Edição
          </Button>
          <Button
            variant="contained"
            color="secondary"
            onClick={handleResetEdit}
            className="reset-edit-button"
            style={{ marginLeft: '10px' }}
          >
            Resetar Edição
          </Button>
        </div>
      </div>
    </Container>
  );
}

export default Home;
