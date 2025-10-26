/**
 * JavaScript para tabela de solicitações - Versão Limpa
 * Sistema de Gestão de Estoque
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('🔄 Inicializando tabela de solicitações...');
    
    initSelectAll();
    initAtualizarTabela();
    initImprimir();
    verificarItensEmImpressaoPendente();
    
    console.log('✅ Tabela inicializada com sucesso!');
});

/**
 * Configurar seleção de todos os checkboxes
 */
function initSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const checkboxes = document.querySelectorAll('.solicitacao-checkbox');
    
    if (!selectAllCheckbox || !checkboxes.length) return;
    
    selectAllCheckbox.addEventListener('change', function() {
        checkboxes.forEach(checkbox => {
            checkbox.checked = this.checked;
        });
    });
    
    // Atualizar checkbox principal quando individuais mudarem
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const allChecked = Array.from(checkboxes).every(cb => cb.checked);
            const someChecked = Array.from(checkboxes).some(cb => cb.checked);
            
            selectAllCheckbox.checked = allChecked;
            selectAllCheckbox.indeterminate = someChecked && !allChecked;
        });
    });
}


/**
 * Mostrar notificação
 */
function showNotification(message, type = 'info') {
    // Criar elemento de notificação
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    `;
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Remover após 5 segundos
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

/**
 * Adicionar efeitos visuais
 */
function addVisualEffects() {
    // Efeito de hover nas linhas
    const rows = document.querySelectorAll('.table-modern tbody tr');
    rows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.transform = 'translateX(4px)';
            this.style.transition = 'transform 0.2s ease';
        });
        
        row.addEventListener('mouseleave', function() {
            this.style.transform = 'translateX(0)';
        });
    });
}

/**
 * Configurar botão de atualizar tabela
 */
function initAtualizarTabela() {
    const btnAtualizar = document.getElementById('btnAtualizarTabela');
    if (!btnAtualizar) return;
    
    btnAtualizar.addEventListener('click', function() {
        atualizarTabela();
    });
}

/**
 * Atualizar tabela com progresso
 */
function atualizarTabela() {
    const btnAtualizar = document.getElementById('btnAtualizarTabela');
    const btnText = document.getElementById('btnText');
    const modal = new bootstrap.Modal(document.getElementById('modalCarregamento'));
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const statusText = document.getElementById('statusText');
    
    // Função para restaurar estado do botão
    function restaurarBotao() {
        btnAtualizar.disabled = false;
        btnText.innerHTML = '<i class="fas fa-sync-alt me-1"></i>Atualizar Tabela';
    }
    
    // Desabilitar botão
    btnAtualizar.disabled = true;
    btnText.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Atualizando...';
    
    // Mostrar modal
    modal.show();
    
    // Simular progresso
    let progress = 0;
    const interval = setInterval(() => {
        try {
            progress += Math.random() * 15;
            if (progress > 100) progress = 100;
            
            progressBar.style.width = progress + '%';
            progressBar.setAttribute('aria-valuenow', progress);
            progressText.textContent = Math.round(progress) + '%';
            
            // Atualizar status
            if (progress < 20) {
                statusText.textContent = 'Conectando com Google Sheets...';
            } else if (progress < 40) {
                statusText.textContent = 'Lendo dados das Solicitações...';
            } else if (progress < 60) {
                statusText.textContent = 'Lendo dados da Matriz...';
            } else if (progress < 80) {
                statusText.textContent = 'Processando dados da matriz...';
            } else if (progress < 95) {
                statusText.textContent = 'Sincronizando informações...';
            } else {
                statusText.textContent = 'Finalizando atualização...';
            }
            
            if (progress >= 100) {
                clearInterval(interval);
                
                // Restaurar estado do botão
                restaurarBotao();
                
                // Aguardar um pouco antes de redirecionar
                setTimeout(() => {
                    modal.hide();
                    
                    // Redirecionar para a rota de sincronização
                    window.location.href = '/sincronizar-matriz';
                }, 500);
            }
        } catch (error) {
            console.error('Erro durante atualização:', error);
            clearInterval(interval);
            restaurarBotao();
            modal.hide();
        }
    }, 200);
}

/**
 * Configurar botão de impressão
 */
function initImprimir() {
    const btnImprimir = document.getElementById('btnImprimir');
    if (!btnImprimir) return;
    
    btnImprimir.addEventListener('click', function() {
        imprimirSolicitacoes();
    });
}

/**
 * Função para abrir formulário de impressão
 */
function imprimirSolicitacoes() {
    console.log('🖨️ Abrindo formulário de impressão...');
    
    // Verificar se há checkboxes selecionados
    const checkboxesSelecionados = document.querySelectorAll('.solicitacao-checkbox:checked');
    
    if (checkboxesSelecionados.length === 0) {
        showNotification('Selecione pelo menos uma solicitação para imprimir', 'warning');
        return;
    }
    
    // Verificar se há itens bloqueados (desabilitados)
    const itensBloqueados = Array.from(checkboxesSelecionados).filter(checkbox => checkbox.disabled);
    
    if (itensBloqueados.length > 0) {
        showNotification(`❌ ${itensBloqueados.length} item(ns) selecionado(s) não podem ser impressos. Verifique os itens destacados na tabela.`, 'error');
        return;
    }
    
    // Coletar IDs das solicitações selecionadas
    const idsSelecionados = Array.from(checkboxesSelecionados).map(checkbox => checkbox.value);
    console.log(`📋 ${idsSelecionados.length} solicitações selecionadas para impressão:`, idsSelecionados);
    
    // Criar URL com os IDs selecionados
    const idsParam = idsSelecionados.join(',');
    const url = `/formulario-impressao?ids=${encodeURIComponent(idsParam)}`;
    
    // Mostrar modal de carregamento
    const modal = new bootstrap.Modal(document.getElementById('modalCarregamentoImpressao'));
    const progressBar = document.getElementById('progressBarImpressao');
    const progressText = document.getElementById('progressTextImpressao');
    const statusText = document.getElementById('statusTextImpressao');
    
    modal.show();
    
    // Simular progresso
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 100) progress = 100;
        
        progressBar.style.width = progress + '%';
        progressBar.setAttribute('aria-valuenow', progress);
        progressText.textContent = Math.round(progress) + '%';
        
        // Atualizar status
        if (progress < 20) {
            statusText.textContent = 'Criando romaneio de separação...';
        } else if (progress < 40) {
            statusText.textContent = 'Processando dados das solicitações...';
        } else if (progress < 60) {
            statusText.textContent = 'Gerando formulário de impressão...';
        } else if (progress < 80) {
            statusText.textContent = 'Preparando para impressão...';
        } else if (progress < 95) {
            statusText.textContent = 'Atualizando status para "Em Separação"...';
        } else {
            statusText.textContent = 'Finalizando processamento...';
        }
        
        if (progress >= 100) {
            clearInterval(interval);
        }
    }, 200);
    
    // Fazer requisição para criar o romaneio e obter o HTML
    console.log('🔄 Fazendo requisição para:', url);
    fetch(url, {
        method: 'GET',
        headers: {
            'X-CSRFToken': document.querySelector('meta[name=csrf-token]')?.getAttribute('content') || ''
        }
    })
    .then(response => {
        console.log('📡 Resposta recebida:', response.status, response.statusText);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.text();
    })
    .then(html => {
        console.log('📄 HTML recebido, tamanho:', html.length, 'caracteres');
        
        // Aguardar um pouco para mostrar o progresso
        setTimeout(() => {
            // Criar uma nova janela temporária para impressão
            const printWindow = window.open('', '_blank', 'width=1200,height=800');
            
            if (!printWindow) {
                modal.hide();
                showNotification('Erro: Não foi possível abrir janela de impressão. Verifique se o bloqueador de pop-ups está desabilitado.', 'error');
                return;
            }
            
            console.log('🪟 Janela de impressão criada');
            
            // Escrever o HTML na nova janela
            printWindow.document.write(html);
            printWindow.document.close();
            
            console.log('📝 HTML escrito na janela');
            
            // Aguardar o carregamento e imprimir
            printWindow.onload = function() {
                console.log('🖨️ Iniciando impressão...');
                printWindow.focus();
                printWindow.print();
                
                // Fechar a janela após impressão
                setTimeout(() => {
                    console.log('🔒 Fechando janela de impressão');
                    printWindow.close();
                }, 1000);
            };
            
            // Fechar modal e mostrar sucesso
            modal.hide();
            showNotification(`Romaneio de separação criado com ${idsSelecionados.length} solicitação(ões)`, 'success');
            
            // Mostrar indicador de atualização após impressão
            setTimeout(() => {
                console.log('🔄 Atualizando informações...');
                showNotification('Atualizando informações da tabela...', 'info');
                
                // Mostrar indicador de atualização
                mostrarIndicadorAtualizacao();
                
                // Recarregar a página após mostrar o indicador
                setTimeout(() => {
                    console.log('🔄 Recarregando página para mostrar status atualizados...');
                    window.location.reload();
                }, 1500);
            }, 1000);
        }, 1000);
    })
    .catch(error => {
        console.error('❌ Erro ao processar impressão:', error);
        modal.hide();
        
        // Remover overlay de loading se existir
        removerIndicadorAtualizacao();
        
        showNotification(`Erro ao processar impressão: ${error.message}`, 'error');
    });
}

/**
 * Mostrar indicador de atualização de informações
 */
function mostrarIndicadorAtualizacao() {
    // Remover overlay existente se houver
    const existingOverlay = document.getElementById('loadingOverlay');
    if (existingOverlay) {
        existingOverlay.remove();
    }
    
    // Criar novo overlay
    const loadingOverlay = document.createElement('div');
    loadingOverlay.id = 'loadingOverlay';
    loadingOverlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    `;
    
    loadingOverlay.innerHTML = `
        <div style="background: white; padding: 2rem; border-radius: 10px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.3);">
            <div class="spinner-border text-primary mb-3" role="status" style="width: 3rem; height: 3rem;">
                <span class="visually-hidden">Carregando...</span>
            </div>
            <h5 class="text-primary mb-2">Atualizando Informações</h5>
            <p class="text-muted mb-0">Atualizando status das solicitações...</p>
        </div>
    `;
    
    document.body.appendChild(loadingOverlay);
    return loadingOverlay;
}

/**
 * Remover indicador de atualização
 */
function removerIndicadorAtualizacao() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.remove();
    }
}

/**
 * Alterar status das solicitações selecionadas para "Em Separação" após impressão
 */
function alterarStatusAposImpressao(idsSelecionados) {
    console.log('🔄 Alterando status das solicitações selecionadas para "Em Separação"...');
    console.log('📋 IDs selecionados:', idsSelecionados);
    
    fetch('/alterar-status-impressao', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name=csrf-token]')?.getAttribute('content') || ''
        },
        body: JSON.stringify({
            ids_selecionados: idsSelecionados
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log(`✅ ${data.message}`);
            showNotification(`Status alterado: ${data.message}`, 'success');
            
            // Recarregar a página para mostrar os novos status
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            console.error('❌ Erro ao alterar status:', data.message);
            showNotification(`Erro: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        console.error('❌ Erro na requisição:', error);
        showNotification('Erro ao alterar status das solicitações', 'error');
    });
}

/**
 * Verificar itens que já estão em impressão pendente ou com status "Em Separação"
 */
async function verificarItensEmImpressaoPendente() {
    try {
        console.log('🔍 Verificando itens em impressão pendente e status "Em Separação"...');
        
        const checkboxes = document.querySelectorAll('.solicitacao-checkbox');
        const ids = Array.from(checkboxes).map(cb => cb.value);
        
        console.log('📋 IDs dos checkboxes encontrados:', ids);
        
        if (ids.length === 0) return;
        
        const response = await fetch('/verificar-itens-impressao', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name=csrf-token]').getAttribute('content')
            },
            body: JSON.stringify({ ids: ids })
        });
        
        const data = await response.json();
        
        console.log('📡 Resposta da API:', data);
        
        if (data.success) {
            let totalBloqueados = 0;
            
            // Verificar itens em impressão pendente
            if (data.itens_em_impressao && data.itens_em_impressao.length > 0) {
                console.log(`⚠️ ${data.itens_em_impressao.length} itens já estão em impressão pendente`);
                totalBloqueados += data.itens_em_impressao.length;
                
                data.itens_em_impressao.forEach(id => {
                    const checkbox = document.querySelector(`input[value="${id}"]`);
                    if (checkbox) {
                        checkbox.disabled = true;
                        checkbox.title = 'Este item já está em impressão pendente';
                        
                        // Adicionar classe visual
                        const row = checkbox.closest('tr');
                        if (row) {
                            row.classList.add('table-warning');
                            row.title = 'Item já está em impressão pendente';
                        }
                    }
                });
            }
            
            // Verificar itens com status "Em Separação"
            if (data.itens_em_separacao && data.itens_em_separacao.length > 0) {
                console.log(`⚠️ ${data.itens_em_separacao.length} itens já estão com status "Em Separação"`);
                totalBloqueados += data.itens_em_separacao.length;
                
                data.itens_em_separacao.forEach(id => {
                    console.log(`🔒 Desabilitando checkbox para ID: ${id}`);
                    const checkbox = document.querySelector(`input[value="${id}"]`);
                    if (checkbox) {
                        checkbox.disabled = true;
                        checkbox.title = 'Este item já está com status "Em Separação"';
                        console.log(`✅ Checkbox ${id} desabilitado`);
                        
                        // Adicionar classe visual diferente
                        const row = checkbox.closest('tr');
                        if (row) {
                            row.classList.add('table-info');
                            row.title = 'Item já está com status "Em Separação"';
                            console.log(`✅ Linha destacada para ID: ${id}`);
                        }
                    } else {
                        console.log(`❌ Checkbox não encontrado para ID: ${id}`);
                    }
                });
            }
            
            // Mostrar aviso se houver itens bloqueados
            if (totalBloqueados > 0) {
                let mensagem = `⚠️ ${totalBloqueados} item(ns) não podem ser impressos: `;
                if (data.itens_em_impressao && data.itens_em_impressao.length > 0) {
                    mensagem += `${data.itens_em_impressao.length} em impressão pendente`;
                }
                if (data.itens_em_separacao && data.itens_em_separacao.length > 0) {
                    if (data.itens_em_impressao && data.itens_em_impressao.length > 0) {
                        mensagem += ', ';
                    }
                    mensagem += `${data.itens_em_separacao.length} com status "Em Separação"`;
                }
                
                showNotification(mensagem, 'warning');
            }
        }
        
    } catch (error) {
        console.error('❌ Erro ao verificar itens em impressão pendente:', error);
    }
}

// Inicializar efeitos visuais
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(addVisualEffects, 100);
});