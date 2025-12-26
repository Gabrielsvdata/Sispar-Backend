-- Script SQL para adicionar coluna 'tipo' na tabela colaborador
-- Execute este comando no seu banco de dados MySQL

-- Adicionar coluna 'tipo' com valor padrão 'usuario'
ALTER TABLE colaborador 
ADD COLUMN tipo VARCHAR(20) DEFAULT 'usuario' NOT NULL;

-- (Opcional) Atualizar colaboradores existentes para garantir que todos tenham o tipo 'usuario'
UPDATE colaborador 
SET tipo = 'usuario' 
WHERE tipo IS NULL;

-- (Opcional) Adicionar constraint para validar apenas valores 'usuario' ou 'admin'
ALTER TABLE colaborador 
ADD CONSTRAINT chk_tipo CHECK (tipo IN ('usuario', 'admin'));

-- Verificar se a coluna foi adicionada corretamente
DESCRIBE colaborador;
