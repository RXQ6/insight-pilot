package com.insightpilot.service;

import com.insightpilot.dto.ApiDtos.DatasetResponse;
import com.insightpilot.dto.ApiDtos.PreviewResponse;
import com.insightpilot.entity.Dataset;
import com.insightpilot.repository.DatasetRepository;
import lombok.RequiredArgsConstructor;
import org.postgresql.copy.CopyManager;
import org.postgresql.core.BaseConnection;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import javax.sql.DataSource;
import java.io.IOException;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class DatasetService {

    private static final int MAX_COLUMNS = 50;
    private static final int MAX_ROWS = 100_000;
    private static final long MAX_BYTES = 10L * 1024 * 1024;

    private final DatasetRepository datasetRepository;
    private final JdbcTemplate jdbcTemplate;
    private final DataSource dataSource;

    @Transactional
    public DatasetResponse upload(Long userId, MultipartFile file, String name) throws IOException {
        if (file == null || file.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "file is empty");
        }
        if (file.getSize() > MAX_BYTES) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "file too large");
        }
        String content = new String(file.getBytes(), StandardCharsets.UTF_8);
        List<String[]> rows = parseCsv(content);
        if (rows.size() < 2) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "csv needs header and data rows");
        }
        if (rows.size() - 1 > MAX_ROWS) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "too many rows");
        }
        String[] header = rows.get(0);
        if (header.length == 0 || header.length > MAX_COLUMNS) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid column count");
        }
        List<String> columns = sanitizeColumns(header);
        List<String> types = inferTypes(rows, columns.size());
        String tableName = "dataset_" + userId + "_" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);

        Dataset dataset = new Dataset();
        dataset.setUserId(userId);
        dataset.setName(name == null || name.isBlank() ? file.getOriginalFilename() : name);
        dataset.setTableName(tableName);
        dataset.setRowCount(rows.size() - 1);
        datasetRepository.save(dataset);

        createTable(tableName, columns, types);
        copyData(tableName, columns, rows);
        return toResponse(dataset);
    }

    public List<DatasetResponse> list(Long userId) {
        return datasetRepository.findByUserIdOrderByCreatedAtDesc(userId).stream()
                .map(this::toResponse)
                .toList();
    }

    public PreviewResponse preview(Long userId, Long id) {
        Dataset dataset = owned(userId, id);
        List<String> columns = jdbcTemplate.queryForList(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = ? ORDER BY ordinal_position",
                String.class,
                dataset.getTableName());
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT * FROM \"" + dataset.getTableName() + "\" LIMIT 20");
        return new PreviewResponse(columns, rows);
    }

    @Transactional
    public void delete(Long userId, Long id) {
        Dataset dataset = owned(userId, id);
        jdbcTemplate.execute("DROP TABLE IF EXISTS \"" + dataset.getTableName() + "\"");
        datasetRepository.delete(dataset);
    }

    private Dataset owned(Long userId, Long id) {
        Dataset dataset = datasetRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "dataset not found"));
        if (!dataset.getUserId().equals(userId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "forbidden");
        }
        return dataset;
    }

    private void createTable(String tableName, List<String> columns, List<String> types) {
        StringBuilder ddl = new StringBuilder("CREATE TABLE \"").append(tableName).append("\" (");
        for (int i = 0; i < columns.size(); i++) {
            ddl.append("\"").append(columns.get(i)).append("\" ").append(types.get(i));
            if (i < columns.size() - 1) {
                ddl.append(", ");
            }
        }
        ddl.append(")");
        jdbcTemplate.execute(ddl.toString());
    }

    private void copyData(String tableName, List<String> columns, List<String[]> rows) throws IOException {
        StringBuilder data = new StringBuilder();
        for (int i = 1; i < rows.size(); i++) {
            data.append(toCsvLine(rows.get(i))).append('\n');
        }
        String columnList = columns.stream()
                .map(column -> "\"" + column + "\"")
                .reduce((left, right) -> left + ", " + right)
                .orElseThrow(() -> new IllegalStateException("no columns"));
        String sql = "COPY \"" + tableName + "\" (" + columnList + ") FROM STDIN WITH (FORMAT csv, HEADER false)";
        Connection connection = DataSourceUtils.getConnection(dataSource);
        try {
            org.postgresql.PGConnection pgConnection = connection.unwrap(org.postgresql.PGConnection.class);
            CopyManager copyManager = new CopyManager((BaseConnection) pgConnection);
            copyManager.copyIn(sql, new StringReader(data.toString()));
        } catch (SQLException e) {
            throw new IllegalStateException("csv copy failed", e);
        } finally {
            DataSourceUtils.releaseConnection(connection, dataSource);
        }
    }

    private List<String> sanitizeColumns(String[] header) {
        Set<String> used = new HashSet<>();
        List<String> result = new ArrayList<>();
        for (int i = 0; i < header.length; i++) {
            String base = header[i].trim().replace("\uFEFF", "")
                    .toLowerCase(Locale.ROOT)
                    .replaceAll("[^a-z0-9_]", "_")
                    .replaceAll("_+", "_")
                    .replaceAll("^_|_$", "");
            if (base.isEmpty() || Character.isDigit(base.charAt(0))) {
                base = "col_" + base;
            }
            String candidate = base;
            int suffix = 1;
            while (!used.add(candidate)) {
                candidate = base + "_" + suffix;
                suffix++;
            }
            result.add(candidate);
        }
        return result;
    }

    private List<String> inferTypes(List<String[]> rows, int columnCount) {
        List<String> types = new ArrayList<>();
        for (int col = 0; col < columnCount; col++) {
            boolean allInt = true;
            boolean allNum = true;
            int sampled = 0;
            for (int row = 1; row < rows.size() && sampled < 100; row++, sampled++) {
                String value = rows.get(row)[col].trim();
                if (value.isEmpty()) {
                    continue;
                }
                if (!value.matches("-?\\d+")) {
                    allInt = false;
                }
                if (!value.matches("-?\\d+(\\.\\d+)?")) {
                    allNum = false;
                }
            }
            if (allInt) {
                types.add("BIGINT");
            } else if (allNum) {
                types.add("NUMERIC(18,2)");
            } else {
                types.add("TEXT");
            }
        }
        return types;
    }

    private List<String[]> parseCsv(String content) {
        List<String[]> rows = new ArrayList<>();
        List<String> current = new ArrayList<>();
        StringBuilder field = new StringBuilder();
        boolean inQuotes = false;
        for (int i = 0; i < content.length(); i++) {
            char ch = content.charAt(i);
            if (inQuotes) {
                if (ch == '"') {
                    if (i + 1 < content.length() && content.charAt(i + 1) == '"') {
                        field.append('"');
                        i++;
                    } else {
                        inQuotes = false;
                    }
                } else {
                    field.append(ch);
                }
            } else if (ch == '"') {
                inQuotes = true;
            } else if (ch == ',') {
                current.add(field.toString());
                field.setLength(0);
            } else if (ch == '\n') {
                current.add(field.toString());
                field.setLength(0);
                rows.add(current.toArray(new String[0]));
                current = new ArrayList<>();
            } else if (ch != '\r') {
                field.append(ch);
            }
        }
        if (field.length() > 0 || !current.isEmpty()) {
            current.add(field.toString());
            rows.add(current.toArray(new String[0]));
        }
        return rows;
    }

    private String toCsvLine(String[] values) {
        StringBuilder line = new StringBuilder();
        for (int i = 0; i < values.length; i++) {
            String value = values[i];
            boolean needsQuote = value.contains(",") || value.contains("\"") || value.contains("\n");
            if (needsQuote) {
                line.append('"').append(value.replace("\"", "\"\"")).append('"');
            } else {
                line.append(value);
            }
            if (i < values.length - 1) {
                line.append(',');
            }
        }
        return line.toString();
    }

    private DatasetResponse toResponse(Dataset dataset) {
        return new DatasetResponse(dataset.getId(), dataset.getName(), dataset.getTableName(),
                dataset.getRowCount(), dataset.getCreatedAt());
    }
}