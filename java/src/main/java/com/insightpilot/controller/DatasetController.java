package com.insightpilot.controller;

import com.insightpilot.dto.ApiDtos.DatasetResponse;
import com.insightpilot.dto.ApiDtos.PreviewResponse;
import com.insightpilot.service.AuthService;
import com.insightpilot.service.DatasetService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/datasets")
@RequiredArgsConstructor
public class DatasetController {

    private final DatasetService datasetService;
    private final AuthService authService;

    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public DatasetResponse upload(Authentication authentication,
                                  @RequestParam("file") MultipartFile file,
                                  @RequestParam(value = "name", required = false) String name) throws IOException {
        return datasetService.upload(authService.userId(authentication.getName()), file, name);
    }

    @GetMapping
    public Map<String, List<DatasetResponse>> list(Authentication authentication) {
        return Map.of("items", datasetService.list(authService.userId(authentication.getName())));
    }

    @GetMapping("/{id}/preview")
    public PreviewResponse preview(Authentication authentication, @PathVariable Long id) {
        return datasetService.preview(authService.userId(authentication.getName()), id);
    }

    @DeleteMapping("/{id}")
    public Map<String, Boolean> delete(Authentication authentication, @PathVariable Long id) {
        datasetService.delete(authService.userId(authentication.getName()), id);
        return Map.of("deleted", true);
    }
}