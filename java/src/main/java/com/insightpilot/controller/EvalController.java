package com.insightpilot.controller;

import com.insightpilot.dto.ApiDtos.EvalSummary;
import com.insightpilot.entity.EvalRun;
import com.insightpilot.repository.EvalRunRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/eval")
@RequiredArgsConstructor
public class EvalController {

    private final EvalRunRepository evalRunRepository;

    @GetMapping("/summary")
    public EvalSummary summary() {
        EvalRun run = evalRunRepository.findTopByOrderByCreatedAtDesc().orElse(null);
        if (run == null) {
            return new EvalSummary("none", 0, 0, 0.0, 0.0, null);
        }
        return new EvalSummary(
                run.getRunId(),
                run.getTotal(),
                run.getPassed(),
                run.getScore(),
                run.getCostCny(),
                run.getCreatedAt());
    }

    @PostMapping("/run")
    @ResponseStatus(HttpStatus.NOT_IMPLEMENTED)
    public Map<String, String> run() {
        return Map.of("message", "eval runner lives in the agent side");
    }
}
